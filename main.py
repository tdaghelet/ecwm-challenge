#!/usr/bin/env python3
"""
ECWM Challenge - CLI Unifie

Commandes disponibles:
    python main.py                    # Pipeline complet (defaut)
    python main.py sync               # Synchroniser les sources externes
    python main.py sync --ffc         # FFC uniquement
    python main.py sync --ufolep      # UFOLEP uniquement
    python main.py init               # Initialiser coureurs + courses
    python main.py serve              # Serveur web local
"""
import os
import sys
import csv
import json
import argparse
import http.server
import socketserver
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

import pandas as pd

from src.core.config import Config
from src.core.calculator import PointsCalculator
from src.core.badges import BadgeCalculator
from src.core.models import CoureurClassement, CoureurPoints, CourseMetadata
from src.parsers.ufolep import UfolepPDFParser
from src.parsers.manual import ManualParser
from src.parsers.ffc_csv import FFCCSVParser
from src.parsers.cartons import CartonParser
from src.scrapers.ufolep_calendar import UfolepCalendarScraper
from src.scrapers.ffc_scraper import FFCExtractor
from src.core import utils


# ============================================================================
# Pipeline Principal
# ============================================================================

class ECWMPipeline:
    """Pipeline unifie pour le ECWM Challenge"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.extraction_cache = self.cache_dir / "extraction_data.json"
        self.badges_cache = self.cache_dir / "badges_data.json"

    def _get_cache_timestamp(self, cache_file: Path) -> float:
        """Recupere le timestamp du cache"""
        if not cache_file.exists():
            return 0
        return cache_file.stat().st_mtime

    def _get_source_timestamp(self) -> float:
        """Recupere le timestamp le plus recent des sources"""
        timestamps = []

        pdf_dirs = [
            "classements/ufolep/cx-25-26",
            "classements/ufolep/vtt-25-26",
        ]

        for pdf_dir in pdf_dirs:
            if os.path.exists(pdf_dir):
                for pdf_file in Path(pdf_dir).glob("*.pdf"):
                    timestamps.append(pdf_file.stat().st_mtime)

        config_files = [
            "config/coureurs.csv",
            "config/courses.csv",
            "config/points.csv",
            "config/sources_manuelles.csv",
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                timestamps.append(Path(config_file).stat().st_mtime)

        return max(timestamps) if timestamps else 0

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Verifie si le cache est encore valide"""
        if not cache_file.exists():
            return False
        cache_time = self._get_cache_timestamp(cache_file)
        source_time = self._get_source_timestamp()
        return cache_time > source_time

    def _run_extraction(self) -> Dict[str, CoureurClassement]:
        """Execute l'extraction complete"""
        config = Config()
        parser = UfolepPDFParser()
        manual_parser = ManualParser()
        ffc_parser = FFCCSVParser()
        calculator = PointsCalculator(config)

        classements = {}
        for coureur in config.coureurs:
            nom_norm = utils.normalize_name(coureur)
            classements[nom_norm] = CoureurClassement(nom=coureur)

        # PDFs UFOLEP CX
        cx_dir = "classements/ufolep/cx-25-26"
        if os.path.exists(cx_dir):
            print(f"\n   Extraction - {cx_dir}")
            print("-" * 70)
            self._process_all_pdfs(cx_dir, "cx", parser, calculator, config, classements)

        # PDFs UFOLEP VTT
        vtt_dir = "classements/ufolep/vtt-25-26"
        if os.path.exists(vtt_dir):
            print(f"\n   Extraction - {vtt_dir}")
            print("-" * 70)
            self._process_all_pdfs(vtt_dir, "vtt", parser, calculator, config, classements)

        # CSV FFC CX
        ffc_cx_dir = "classements/ffc/cx-25-26"
        if os.path.exists(ffc_cx_dir):
            print(f"\n   Extraction - {ffc_cx_dir}")
            print("-" * 70)
            self._process_all_csvs(ffc_cx_dir, "cx", ffc_parser, calculator, config, classements)

        # CSV FFC Route
        ffc_route_dir = "classements/ffc/route-25-26"
        if os.path.exists(ffc_route_dir):
            print(f"\n   Extraction - {ffc_route_dir}")
            print("-" * 70)
            self._process_all_csvs(ffc_route_dir, "route", ffc_parser, calculator, config, classements)

        # Saisies manuelles
        self._process_manual_entries(manual_parser, calculator, config, classements)

        # Finaliser
        print("\n   Finalisation des totaux")
        print("-" * 70)
        for coureur_classement in classements.values():
            coureur_classement.update_totals(0)
        print(f"   {len(classements)} coureurs finalises")

        self._print_top10(classements)

        return classements

    def _process_all_pdfs(self, directory: str, discipline: str,
                          parser: UfolepPDFParser, calculator: PointsCalculator,
                          config: Config, classements: Dict[str, CoureurClassement]) -> None:
        """Traite tous les PDFs d'un repertoire"""
        pdf_dir = Path(directory)
        pdf_files = sorted(pdf_dir.glob("*.pdf"), key=lambda x: x.name)
        print(f"   {len(pdf_files)} fichiers PDF\n")

        for pdf_path in pdf_files:
            course_name = utils.extract_course_name(pdf_path.name)
            self._process_pdf(str(pdf_path), course_name, discipline,
                             parser, calculator, config, classements)
        print()

    def _process_pdf(self, pdf_path: str, course_name: str, discipline: str,
                     parser: UfolepPDFParser, calculator: PointsCalculator,
                     config: Config, classements: Dict[str, CoureurClassement]) -> None:
        """Traite un PDF de course"""
        categories = parser.parse_course(pdf_path)
        if not categories:
            return

        metadata = config.get_course_metadata(course_name, discipline)
        federation = metadata.federation if metadata else "ufolep"
        is_objectif = metadata.is_objectif if metadata else False

        objectif_marker = " *" if is_objectif else ""
        nb_coureurs_trouves = 0

        for coureur in config.coureurs:
            if not config.coureur_autorise(coureur, discipline, federation):
                continue

            nom_norm = utils.normalize_name(coureur)
            resultat = parser.find_coureur_in_categories(nom_norm, categories)

            if resultat:
                nb_coureurs_trouves += 1
                course_points = calculator.calculate_course_points(
                    coureur=coureur,
                    course_name=course_name,
                    resultat=resultat,
                    discipline=discipline,
                    course_metadata=metadata
                )
                classements[nom_norm].add_course(course_points)

        print(f"   {course_name.upper():25s} {nb_coureurs_trouves:2d} coureurs{objectif_marker}")

    def _process_all_csvs(self, directory: str, discipline: str,
                          parser: FFCCSVParser, calculator: PointsCalculator,
                          config: Config, classements: Dict[str, CoureurClassement]) -> None:
        """Traite tous les CSV d'un repertoire (FFC)"""
        csv_dir = Path(directory)
        csv_files = sorted(csv_dir.glob("*.csv"), key=lambda x: x.name)
        print(f"   {len(csv_files)} fichiers CSV\n")

        for csv_path in csv_files:
            course_name = utils.extract_course_name(csv_path.name)
            self._process_csv(str(csv_path), course_name, discipline,
                             parser, calculator, config, classements)
        print()

    def _process_csv(self, csv_path: str, course_name: str, discipline: str,
                     parser: FFCCSVParser, calculator: PointsCalculator,
                     config: Config, classements: Dict[str, CoureurClassement]) -> None:
        """Traite un CSV FFC"""
        resultats, date_course = parser.parse_course_csv(csv_path)
        if not resultats:
            return

        metadata = config.get_course_metadata(course_name, discipline)

        if metadata is None:
            metadata = CourseMetadata(
                nom=course_name, discipline=discipline, federation="ffc",
                is_objectif=False, saison="25-26", date_course=date_course
            )
        elif date_course and not metadata.date_course:
            metadata = CourseMetadata(
                nom=metadata.nom, discipline=metadata.discipline,
                federation=metadata.federation, is_objectif=metadata.is_objectif,
                saison=metadata.saison, date_course=date_course
            )

        federation = metadata.federation
        is_objectif = metadata.is_objectif
        objectif_marker = " *" if is_objectif else ""
        nb_coureurs_trouves = 0

        for coureur in config.coureurs:
            if not config.coureur_autorise(coureur, discipline, federation):
                continue

            nom_norm = utils.normalize_name(coureur)
            resultat = parser.find_coureur_in_results(nom_norm, resultats)

            if resultat:
                nb_coureurs_trouves += 1
                course_points = calculator.calculate_course_points(
                    coureur=coureur, course_name=course_name, resultat=resultat,
                    discipline=discipline, course_metadata=metadata
                )
                classements[nom_norm].add_course(course_points)

        print(f"   {course_name.upper():25s} {nb_coureurs_trouves:2d} coureurs{objectif_marker}")

    def _process_manual_entries(self, manual_parser: ManualParser,
                                 calculator: PointsCalculator, config: Config,
                                 classements: Dict[str, CoureurClassement]) -> None:
        """Traite les saisies manuelles"""
        manual_results = manual_parser.load_all_sources()

        if not manual_results:
            return

        nb_resultats = 0
        courses_info = {}

        for result in manual_results:
            coureur_trouve = None
            for coureur in config.coureurs:
                if utils.normalize_name(coureur) == result.coureur:
                    coureur_trouve = coureur
                    break

            if not coureur_trouve:
                continue

            manual_metadata = config.get_course_metadata(result.course_name, result.discipline)
            date_course = result.date or (manual_metadata.date_course if manual_metadata else None)

            if manual_metadata is None:
                manual_metadata = CourseMetadata(
                    nom=result.course_name, discipline=result.discipline,
                    federation=result.federation, is_objectif=False,
                    saison="25-26", date_course=date_course
                )
            elif date_course and manual_metadata.date_course != date_course:
                manual_metadata = CourseMetadata(
                    nom=manual_metadata.nom, discipline=manual_metadata.discipline,
                    federation=manual_metadata.federation, is_objectif=manual_metadata.is_objectif,
                    saison=manual_metadata.saison, date_course=date_course
                )

            key = (result.course_name, result.discipline)
            if key not in courses_info:
                courses_info[key] = {
                    'course_name': result.course_name,
                    'discipline': result.discipline,
                    'federation': result.federation,
                    'date_course': date_course
                }

            course_points = calculator.calculate_course_points_manual(
                coureur=coureur_trouve, course_name=result.course_name,
                position=result.position, nb_participants=result.nb_participants,
                categorie=result.categorie or "Saisie manuelle",
                discipline=result.discipline, course_metadata=manual_metadata
            )

            nom_norm = utils.normalize_name(coureur_trouve)
            classements[nom_norm].add_course(course_points)
            nb_resultats += 1

        if courses_info:
            self._update_courses_metadata(list(courses_info.values()))

        print(f"   {nb_resultats} resultats manuels traites")
        print()

    def _update_courses_metadata(self, courses_info: list,
                                  metadata_path: str = "config/courses.csv") -> int:
        """Met a jour courses.csv avec les courses des saisies manuelles"""
        rows = []
        fieldnames = ['nom', 'discipline', 'federation', 'is_objectif', 'saison', 'date_course']

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    fieldnames = list(reader.fieldnames)
                    if 'date_course' not in fieldnames:
                        fieldnames.append('date_course')
                rows = list(reader)

        existing_courses = {}
        for i, row in enumerate(rows):
            nom = row['nom'].strip().lower()
            discipline = row['discipline'].strip().lower()
            existing_courses[(nom, discipline)] = i

        added = 0
        updated = 0

        for info in courses_info:
            course_name = info['course_name'].strip().lower()
            discipline = info['discipline'].strip().lower()
            date_course = info.get('date_course') or ''
            federation = info.get('federation', 'ufolep').strip().lower()

            key = (course_name, discipline)

            if key in existing_courses:
                idx = existing_courses[key]
                old_date = rows[idx].get('date_course', '')
                if date_course and date_course != old_date:
                    rows[idx]['date_course'] = date_course
                    updated += 1
            else:
                new_row = {
                    'nom': course_name, 'discipline': discipline,
                    'federation': federation, 'is_objectif': 'false',
                    'saison': '25-26', 'date_course': date_course
                }
                rows.append(new_row)
                existing_courses[key] = len(rows) - 1
                added += 1

        rows.sort(key=lambda r: (r['nom'].lower(), r['discipline'].lower()))

        with open(metadata_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        if added > 0 or updated > 0:
            print(f"   {added} courses ajoutees, {updated} dates mises a jour")

    def _print_top10(self, classements: Dict[str, CoureurClassement]) -> None:
        """Affiche le TOP 10"""
        print("\n   TOP 10")
        print("=" * 70)

        classement_sorted = sorted(
            classements.values(),
            key=lambda x: x.points_total,
            reverse=True
        )

        for i, coureur in enumerate(classement_sorted[:10], 1):
            medal = {1: "1.", 2: "2.", 3: "3."}.get(i, f"{i:2d}.")
            print(f"   {medal} {coureur.nom:25s} {coureur.points_total:3d} pts ({coureur.nb_courses} courses)")

        print("=" * 70)

    def step1_extract(self, force: bool = False) -> Dict:
        """Etape 1: Extraction des PDFs + saisies manuelles"""
        print("\n" + "=" * 70)
        print("ETAPE 1/2 : EXTRACTION DES DONNEES")
        print("=" * 70)

        if not force and self._is_cache_valid(self.extraction_cache):
            print("   Cache valide, chargement...")
            with open(self.extraction_cache, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            print(f"   {len(cached_data)} coureurs charges depuis le cache\n")
            return cached_data

        print("   Extraction en cours...\n")
        classements = self._run_extraction()

        classements_data = {}
        for nom, coureur in classements.items():
            classements_data[nom] = {
                'nom': coureur.nom,
                'courses_detail': [
                    {
                        'coureur': cp.coureur, 'course': cp.course,
                        'position': cp.position, 'nb_participants': cp.nb_participants,
                        'categorie': cp.categorie, 'discipline': cp.discipline,
                        'federation': cp.federation, 'percentile': cp.percentile,
                        'points_participation': cp.points_participation,
                        'points_performance': cp.points_performance,
                        'coefficient': cp.coefficient, 'bonus_objectif': cp.bonus_objectif,
                        'points_total': cp.points_total, 'date_course': cp.date_course,
                    }
                    for cp in coureur.courses_detail
                ],
                'nb_courses': coureur.nb_courses,
                'nb_courses_objectif': coureur.nb_courses_objectif,
                'points_courses': coureur.points_courses,
                'bonus_badges': 0,
                'points_total': coureur.points_total,
            }

        with open(self.extraction_cache, 'w', encoding='utf-8') as f:
            json.dump(classements_data, f, indent=2, ensure_ascii=False)

        print(f"\n   Cache sauvegarde: {self.extraction_cache}")
        return classements_data

    def step2_generate_site(self, classements_data: Dict) -> Dict:
        """Etape 2: Calcul des badges et generation du site"""
        print("\n" + "=" * 70)
        print("ETAPE 2/2 : BADGES ET SITE")
        print("=" * 70)

        config = Config()

        # Reconstruire les objets
        classements_objets = {}
        for nom, data in classements_data.items():
            coureur = CoureurClassement(nom=data['nom'])
            coureur.courses_detail = [CoureurPoints(**cp) for cp in data['courses_detail']]
            coureur.nb_courses = data['nb_courses']
            coureur.nb_courses_objectif = data['nb_courses_objectif']
            coureur.points_courses = data['points_courses']
            coureur.bonus_badges = data['bonus_badges']
            coureur.points_total = data['points_total']
            classements_objets[nom] = coureur

        # Calculer les badges
        badge_calculator = BadgeCalculator()
        courses_metadata_dict = config.courses_metadata
        total_courses_saison = len(courses_metadata_dict)

        badges_par_coureur = {}
        for nom_norm, coureur in classements_objets.items():
            badges_obtenus = badge_calculator.calculate_badges(
                coureur, courses_metadata_dict, total_courses_saison
            )
            bonus_total = sum(badge.bonus_points for badge in badges_obtenus)

            badges_par_coureur[nom_norm] = {
                'bonus_total': bonus_total,
                'badges_obtenus': [
                    {
                        'badge_id': b.badge_id, 'nom': b.nom, 'emoji': b.emoji,
                        'description': b.description, 'niveau': b.niveau,
                        'valeur_obtenue': b.valeur_obtenue, 'bonus_points': b.bonus_points,
                    }
                    for b in badges_obtenus
                ]
            }

            classements_data[nom_norm]['bonus_badges'] = bonus_total
            classements_data[nom_norm]['points_total'] = (
                classements_data[nom_norm]['points_courses'] + bonus_total
            )

        with open(self.badges_cache, 'w', encoding='utf-8') as f:
            json.dump(badges_par_coureur, f, indent=2, ensure_ascii=False)

        print(f"   {len(badges_par_coureur)} coureurs avec badges calcules")

        # Generer le JSON du site
        coureurs_data = []
        for nom, coureur_data in classements_data.items():
            coureur_badges = badges_par_coureur.get(nom, {})
            coureur_json = {
                'nom': coureur_data['nom'],
                'nb_courses': coureur_data['nb_courses'],
                'nb_courses_objectif': coureur_data['nb_courses_objectif'],
                'points_courses': round(coureur_data['points_courses'], 1),
                'bonus_badges': coureur_data['bonus_badges'],
                'points_total': round(coureur_data['points_total'], 1),
                'courses_detail': [
                    {
                        'course': cp['course'], 'position': cp['position'],
                        'nb_participants': cp['nb_participants'],
                        'categorie': cp['categorie'], 'discipline': cp['discipline'],
                        'federation': cp['federation'],
                        'percentile': round(cp['percentile'] * 100, 1),
                        'points_participation': round(cp['points_participation'], 1),
                        'points_performance': round(cp['points_performance'], 1),
                        'coefficient': cp['coefficient'],
                        'bonus_objectif': cp['bonus_objectif'],
                        'points': round(cp['points_total'], 1),
                        'date_course': cp.get('date_course'),
                    }
                    for cp in coureur_data['courses_detail']
                ],
                'badges': [
                    {
                        'badge_id': badge['badge_id'], 'nom': badge['nom'],
                        'emoji': badge['emoji'], 'description': badge['description'],
                        'niveau': badge['niveau'], 'valeur_obtenue': badge['valeur_obtenue'],
                        'bonus_points': badge['bonus_points'],
                    }
                    for badge in coureur_badges.get('badges_obtenus', [])
                ]
            }
            coureurs_data.append(coureur_json)

        coureurs_data.sort(key=lambda c: c['points_total'], reverse=True)

        for i, coureur in enumerate(coureurs_data, 1):
            coureur['rang'] = i

        # Liste des courses
        courses_stats = {}
        for coureur_data in classements_data.values():
            for cp in coureur_data['courses_detail']:
                key = (cp['course'], cp['discipline'], cp['federation'])
                if key not in courses_stats:
                    metadata = config.get_course_metadata(cp['course'], cp['discipline'])
                    courses_stats[key] = {
                        'nb_participants': 0,
                        'is_objectif': metadata.is_objectif if metadata else False,
                        'date_course': cp.get('date_course') or (metadata.date_course if metadata else None)
                    }
                courses_stats[key]['nb_participants'] += 1
                if cp.get('date_course') and not courses_stats[key]['date_course']:
                    courses_stats[key]['date_course'] = cp.get('date_course')

        courses_list = []
        for (nom, discipline, federation), stats in courses_stats.items():
            courses_list.append({
                'nom': nom, 'discipline': discipline, 'federation': federation,
                'is_objectif': stats['is_objectif'],
                'nb_participants': stats['nb_participants'],
                'date_course': stats['date_course']
            })

        courses_list.sort(key=lambda c: (c.get('date_course') or '9999-12-31', c['nom']), reverse=True)

        # Config badges
        badges_config_list = []
        for badge in badge_calculator.badges:
            badges_config_list.append({
                'badge_id': badge.badge_id, 'nom': badge.nom, 'emoji': badge.emoji,
                'description': badge.description, 'type': badge.type,
                'critere': badge.critere, 'niveau': badge.niveau,
                'seuil': badge.seuil, 'bonus_points': badge.bonus_points,
                'actif': badge.actif
            })

        site_data = {
            'meta': {
                'derniere_maj': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'nb_coureurs': len(coureurs_data),
                'nb_courses': len(courses_stats),
            },
            'coureurs': coureurs_data,
            'courses': courses_list,
            'badges_config': badges_config_list,
            'config': {
                'points_participation': config.points_params.get('points_participation', 25),
                'points_performance_max': config.points_params.get('points_performance_max', 25),
                'bonus_objectif': config.points_params.get('bonus_objectif', 1.5),
            }
        }

        output_path = "docs/data.json"
        os.makedirs("docs", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(site_data, f, indent=2, ensure_ascii=False)

        print(f"   JSON genere: {output_path}")
        print(f"   {len(coureurs_data)} coureurs, {len(courses_list)} courses")

        return badges_par_coureur

    def run_full_pipeline(self, force_extract: bool = False) -> None:
        """Execute le workflow complet"""
        print("\n")
        print("=" * 70)
        print("            ECWM CHALLENGE - PIPELINE COMPLET")
        print("=" * 70)

        classements_data = self.step1_extract(force=force_extract)
        self.step2_generate_site(classements_data)

        print("\n" + "=" * 70)
        print("PIPELINE TERMINE")
        print("=" * 70)
        print("\nFichiers generes:")
        print("   docs/data.json  -> Donnees pour le site web")
        print("\nPour lancer le serveur local:")
        print("   python main.py serve")
        print()


# ============================================================================
# Commandes CLI
# ============================================================================

def validate_courses_metadata(metadata_path: str = "config/courses.csv") -> None:
    """Valide courses.csv et affiche les courses avec données manquantes"""
    if not os.path.exists(metadata_path):
        print(f"\n⚠️  Fichier {metadata_path} introuvable")
        return

    print("\n" + "=" * 70)
    print("VALIDATION DES MÉTADONNÉES")
    print("=" * 70)

    df = pd.read_csv(metadata_path)

    # Vérifier les dates manquantes
    missing_dates = df[df['date_course'].isna() | (df['date_course'] == '')]

    if len(missing_dates) > 0:
        print(f"\n⚠️  {len(missing_dates)} course(s) sans date :")
        for _, row in missing_dates.iterrows():
            fed = row['federation'].upper()
            disc = row['discipline'].upper()
            print(f"   - {row['nom']:30s} ({fed} {disc})")
        print("\n   💡 Action recommandée : ajouter manuellement les dates dans courses.csv")
    else:
        print("\n✅ Toutes les courses ont une date")

    # Stats globales
    total = len(df)
    with_dates = len(df[df['date_course'].notna() & (df['date_course'] != '')])
    print(f"\n   Total: {total} courses, {with_dates} avec date ({with_dates*100//total}%)")
    print("=" * 70)


def run_sync_courses(args):
    """Commande sync-courses: synchroniser les courses et télécharger les résultats"""
    print("\n")
    print("=" * 70)
    print("            SYNCHRONISATION DES COURSES")
    print("=" * 70)

    if args.ffc or not args.ufolep:
        # Sync FFC
        extractor = FFCExtractor()
        extractor.run(force_extract=args.force, dry_run=args.dry_run)

    if args.ufolep or not args.ffc:
        # Sync UFOLEP
        print("\n" + "=" * 70)
        print("SYNCHRONISATION UFOLEP")
        print("=" * 70)

        scraper = UfolepCalendarScraper()

        if args.dry_run:
            for discipline in ['cx', 'vtt']:
                entries = scraper.scrape_calendar(discipline)
                print(f"\n[DRY RUN] {discipline.upper()}: {len(entries)} courses")
                for entry in entries[:5]:
                    status = "PDF" if entry.pdf_url else "Pas de PDF"
                    print(f"   - {entry.date}: {entry.lieu} [{status}]")
                if len(entries) > 5:
                    print(f"   ... et {len(entries) - 5} autres")
        else:
            all_entries = scraper.run_full_sync(
                output_base_dir="classements/ufolep",
                saison="25-26",
                force_download=args.force,
                dry_run=False
            )
            total = sum(len(e) for e in all_entries.values())
            print(f"\n   {total} courses synchronisees")

    print("\n" + "=" * 70)
    print("SYNCHRONISATION TERMINEE")
    print("=" * 70)

    # Valider courses.csv
    if not args.dry_run:
        validate_courses_metadata()


def run_init_coureurs(args):
    """Commande init-coureurs: générer la liste des coureurs depuis les cartons"""
    print("\n")
    print("=" * 70)
    print("            INITIALISATION DES COUREURS")
    print("=" * 70)
    print("\n   Génération de coureurs.csv depuis les cartons/licences\n")

    carton_cx = "cartons/carte CC WAMBRECHIES.pdf"
    carton_vtt = "cartons/cartes VTT WAMBRECHIES.pdf"
    licences_ffc = "cartons/Liste_Licencies.xlsx"
    output_coureurs = "config/coureurs.csv"

    parser = CartonParser()
    coureurs_dict: Dict[str, Dict[str, bool]] = {}

    # Parser CX UFOLEP
    if Path(carton_cx).exists():
        print(f"   Parsing {carton_cx}")
        coureurs_cx = parser.parse_carton_ufolep(carton_cx)
        print(f"   {len(coureurs_cx)} coureurs trouves")

        for coureur in coureurs_cx:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False, 'ufolep_route': False, 'ufolep_vtt': False,
                    'ffc_cx': False, 'ffc_route': False
                }
            coureurs_dict[coureur.nom_complet]['ufolep_cx'] = True
    else:
        print(f"   {carton_cx} non trouve")

    # Parser VTT UFOLEP
    if Path(carton_vtt).exists():
        print(f"   Parsing {carton_vtt}")
        coureurs_vtt = parser.parse_carton_ufolep(carton_vtt)
        print(f"   {len(coureurs_vtt)} coureurs trouves")

        for coureur in coureurs_vtt:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False, 'ufolep_route': False, 'ufolep_vtt': False,
                    'ffc_cx': False, 'ffc_route': False
                }
            coureurs_dict[coureur.nom_complet]['ufolep_vtt'] = True
    else:
        print(f"   {carton_vtt} non trouve")

    # Parser FFC
    if Path(licences_ffc).exists():
        print(f"   Parsing {licences_ffc}")
        coureurs_ffc = parser.parse_licences_ffc(licences_ffc)
        print(f"   {len(coureurs_ffc)} coureurs trouves")

        for coureur in coureurs_ffc:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False, 'ufolep_route': False, 'ufolep_vtt': False,
                    'ffc_cx': False, 'ffc_route': False
                }
            coureurs_dict[coureur.nom_complet]['ffc_cx'] = True
            coureurs_dict[coureur.nom_complet]['ffc_route'] = True
    else:
        print(f"   {licences_ffc} non trouve")

    # Creer le CSV
    rows = []
    for nom_complet, disciplines in sorted(coureurs_dict.items()):
        rows.append({
            'COUREUR': nom_complet,
            'ufolep_cx': 1 if disciplines['ufolep_cx'] else 0,
            'ufolep_route': 1 if disciplines['ufolep_route'] else 0,
            'ufolep_vtt': 1 if disciplines['ufolep_vtt'] else 0,
            'ffc_cx': 1 if disciplines['ffc_cx'] else 0,
            'ffc_route': 1 if disciplines['ffc_route'] else 0
        })

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output_coureurs, index=False)
        print(f"\n   ✅ Fichier généré: {output_coureurs}")
        print(f"   {len(df)} coureurs au total")
    else:
        print("\n   ⚠️  Aucun coureur trouvé")

    print("\n" + "=" * 70)
    print("INITIALISATION TERMINEE")
    print("=" * 70)
    print("\n   Prochaine étape: python3 main.py sync-courses")


def run_serve(args):
    """Commande serve: lancer le serveur web local"""
    port = args.port
    directory = "docs"

    if not os.path.exists(directory):
        print(f"Le dossier '{directory}' n'existe pas.")
        print("Executez d'abord 'python main.py' pour generer le site.")
        sys.exit(1)

    class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *handler_args, **kwargs):
            super().__init__(*handler_args, directory=directory, **kwargs)

    print("\n")
    print("=" * 50)
    print("       ECWM CHALLENGE - SERVEUR WEB")
    print("=" * 50)
    print(f"   Dossier: {directory}/")
    print(f"   URL: http://localhost:{port}")
    print("\n   Ctrl+C pour arreter")
    print("=" * 50)

    with socketserver.TCPServer(("", port), MyHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n   Serveur arrete")


def main():
    """Point d'entree principal"""
    parser = argparse.ArgumentParser(
        description='ECWM Challenge CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commandes:
  (defaut)        Pipeline complet (extraction + site)
  init-coureurs   Générer coureurs.csv depuis les cartons/licences
  sync-courses    Télécharger les résultats + créer courses.csv avec dates
  serve           Lancer le serveur web local

Exemples:
  python main.py                        # Pipeline complet
  python main.py --skip-cache           # Forcer la réextraction
  python main.py init-coureurs          # Générer coureurs.csv
  python main.py sync-courses           # Télécharger toutes les courses
  python main.py sync-courses --ffc     # FFC uniquement
  python main.py sync-courses --ufolep  # UFOLEP uniquement
  python main.py serve                  # Serveur local sur port 8000
  python main.py serve --port 3000      # Serveur sur port 3000
        """
    )

    # Arguments globaux
    parser.add_argument('--skip-cache', action='store_true',
                       help='Forcer la reextraction (ignorer le cache)')

    # Sous-commandes
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')

    # Commande init-coureurs
    subparsers.add_parser('init-coureurs', help='Générer coureurs.csv depuis les cartons')

    # Commande sync-courses
    sync_parser = subparsers.add_parser('sync-courses', help='Télécharger les résultats et créer courses.csv')
    sync_parser.add_argument('--ffc', action='store_true', help='FFC uniquement')
    sync_parser.add_argument('--ufolep', action='store_true', help='UFOLEP uniquement')
    sync_parser.add_argument('--force', action='store_true', help='Forcer le re-téléchargement')
    sync_parser.add_argument('--dry-run', action='store_true', help='Aperçu sans modification')

    # Commande serve
    serve_parser = subparsers.add_parser('serve', help='Serveur web local')
    serve_parser.add_argument('--port', type=int, default=8000, help='Port (défaut: 8000)')

    args = parser.parse_args()

    if args.command == 'init-coureurs':
        run_init_coureurs(args)
    elif args.command == 'sync-courses':
        run_sync_courses(args)
    elif args.command == 'serve':
        run_serve(args)
    else:
        # Pipeline par defaut
        pipeline = ECWMPipeline()
        pipeline.run_full_pipeline(force_extract=args.skip_cache)


if __name__ == "__main__":
    main()
