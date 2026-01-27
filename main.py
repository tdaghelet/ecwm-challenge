#!/usr/bin/env python3
"""
ECWM Challenge - Script Principal Unifié

Workflow complet:
1. Extraction des PDFs (UFOLEP CX, VTT, FFC)
2. Enrichissement avec les saisies manuelles
3. Calcul des points et des badges
4. Génération du CSV classement + JSON pour le site

Usage:
    python3 main.py                    # Workflow complet
    python3 main.py --skip-cache       # Forcer la réextraction
    python3 main.py --extract-only     # Extraction uniquement
    python3 main.py --generate-only    # Génération site uniquement
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

from src.core.config import Config
from src.core.calculator import PointsCalculator
from src.core.badges import BadgeCalculator
from src.core.models import CoureurClassement, CoureurPoints, CourseMetadata
from src.parsers.ufolep import UfolepPDFParser
from src.parsers.manual import ManualParser
from src.parsers.ffc_csv import FFCCSVParser
from src.core import utils


class ECWMPipeline:
    """Pipeline unifié pour le ECWM Challenge"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Chemins de cache
        self.extraction_cache = self.cache_dir / "extraction_data.json"
        self.badges_cache = self.cache_dir / "badges_data.json"

    def _get_cache_timestamp(self, cache_file: Path) -> float:
        """Récupère le timestamp du cache"""
        if not cache_file.exists():
            return 0
        return cache_file.stat().st_mtime

    def _get_source_timestamp(self) -> float:
        """
        Récupère le timestamp le plus récent des sources de données
        (PDFs, config CSV, sources manuelles)
        """
        timestamps = []

        # PDFs UFOLEP
        pdf_dirs = [
            "classements/ufolep/cx-25-26",
            "classements/ufolep/vtt-25-26",
        ]

        for pdf_dir in pdf_dirs:
            if os.path.exists(pdf_dir):
                for pdf_file in Path(pdf_dir).glob("*.pdf"):
                    timestamps.append(pdf_file.stat().st_mtime)

        # Fichiers de config
        config_files = [
            "data/ecwm_coureurs.csv",
            "data/courses_metadata.csv",
            "data/config_points.csv",
            "data/sources_config.csv",
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                timestamps.append(Path(config_file).stat().st_mtime)

        return max(timestamps) if timestamps else 0

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Vérifie si le cache est encore valide"""
        if not cache_file.exists():
            return False

        cache_time = self._get_cache_timestamp(cache_file)
        source_time = self._get_source_timestamp()

        return cache_time > source_time

    def _run_extraction(self) -> Dict[str, CoureurClassement]:
        """
        Exécute l'extraction complète des PDFs et saisies manuelles

        Returns:
            Dictionnaire des classements par coureur
        """
        # Charger la configuration
        config = Config()

        # Initialiser les parsers
        parser = UfolepPDFParser()
        manual_parser = ManualParser()
        ffc_parser = FFCCSVParser()
        calculator = PointsCalculator(config)

        # Initialiser les classements
        classements = {}
        for coureur in config.coureurs:
            nom_norm = utils.normalize_name(coureur)
            classements[nom_norm] = CoureurClassement(nom=coureur)

        # Traiter les PDFs UFOLEP CX
        cx_dir = "classements/ufolep/cx-25-26"
        if os.path.exists(cx_dir):
            print(f"\n🏁 Extraction des résultats - {cx_dir}")
            print("-" * 70)
            self._process_all_pdfs(cx_dir, "cx", parser, calculator, config, classements)

        # Traiter les PDFs UFOLEP VTT
        vtt_dir = "classements/ufolep/vtt-25-26"
        if os.path.exists(vtt_dir):
            print(f"\n🏁 Extraction des résultats - {vtt_dir}")
            print("-" * 70)
            self._process_all_pdfs(vtt_dir, "vtt", parser, calculator, config, classements)

        # Traiter les CSV FFC CX
        ffc_cx_dir = "classements/ffc/cx-25-26"
        if os.path.exists(ffc_cx_dir):
            print(f"\n🏁 Extraction des résultats - {ffc_cx_dir}")
            print("-" * 70)
            self._process_all_csvs(ffc_cx_dir, "cx", ffc_parser, calculator, config, classements)

        # Traiter les CSV FFC Route
        ffc_route_dir = "classements/ffc/route-25-26"
        if os.path.exists(ffc_route_dir):
            print(f"\n🏁 Extraction des résultats - {ffc_route_dir}")
            print("-" * 70)
            self._process_all_csvs(ffc_route_dir, "route", ffc_parser, calculator, config, classements)

        # Traiter les saisies manuelles
        self._process_manual_entries(manual_parser, calculator, config, classements)

        # Finaliser les totaux
        print("\n🏁 Finalisation des totaux")
        print("-" * 70)
        for coureur_classement in classements.values():
            coureur_classement.update_totals(0)
        print(f"   ✅ Totaux finalisés pour {len(classements)} coureurs")
        print()

        # Afficher le TOP 10
        self._print_top10(classements)

        return classements

    def _process_all_pdfs(
        self,
        directory: str,
        discipline: str,
        parser: UfolepPDFParser,
        calculator: PointsCalculator,
        config: Config,
        classements: Dict[str, CoureurClassement]
    ) -> None:
        """Traite tous les PDFs d'un répertoire"""
        pdf_dir = Path(directory)
        pdf_files = sorted(pdf_dir.glob("*.pdf"), key=lambda x: x.name)

        print(f"   {len(pdf_files)} fichiers PDF trouvés\n")

        for pdf_path in pdf_files:
            course_name = utils.extract_course_name(pdf_path.name)
            self._process_pdf(
                str(pdf_path),
                course_name,
                discipline,
                parser,
                calculator,
                config,
                classements
            )

        print()

    def _process_pdf(
        self,
        pdf_path: str,
        course_name: str,
        discipline: str,
        parser: UfolepPDFParser,
        calculator: PointsCalculator,
        config: Config,
        classements: Dict[str, CoureurClassement]
    ) -> None:
        """Traite un PDF de course"""
        # Parser le PDF
        categories = parser.parse_course(pdf_path)
        if not categories:
            return

        # Récupérer les métadonnées de la course
        metadata = config.get_course_metadata(course_name, discipline)
        federation = metadata.federation if metadata else "ufolep"
        is_objectif = metadata.is_objectif if metadata else False

        # Affichage
        objectif_marker = " ⭐" if is_objectif else ""
        nb_coureurs_trouves = 0

        # Pour chaque coureur ECWM
        for coureur in config.coureurs:
            # Vérifier si autorisé pour cette discipline
            if not config.coureur_autorise(coureur, discipline, federation):
                continue

            nom_norm = utils.normalize_name(coureur)

            # Chercher le coureur dans les catégories
            resultat = parser.find_coureur_in_categories(nom_norm, categories)

            if resultat:
                nb_coureurs_trouves += 1

                # Calculer les points (la méthode attend un objet CoureurResultat)
                course_points = calculator.calculate_course_points(
                    coureur=coureur,
                    course_name=course_name,
                    resultat=resultat,
                    discipline=discipline,
                    course_metadata=metadata
                )

                # Ajouter au classement
                classements[nom_norm].add_course(course_points)

        # Affichage
        course_display = course_name.upper().ljust(25)
        print(f"📄 {course_display}→ {nb_coureurs_trouves:2d} coureurs{objectif_marker}")

    def _process_all_csvs(
        self,
        directory: str,
        discipline: str,
        parser: FFCCSVParser,
        calculator: PointsCalculator,
        config: Config,
        classements: Dict[str, CoureurClassement]
    ) -> None:
        """Traite tous les CSV d'un répertoire (FFC)"""
        csv_dir = Path(directory)
        csv_files = sorted(csv_dir.glob("*.csv"), key=lambda x: x.name)

        print(f"   {len(csv_files)} fichiers CSV trouvés\n")

        for csv_path in csv_files:
            course_name = utils.extract_course_name(csv_path.name)
            self._process_csv(
                str(csv_path),
                course_name,
                discipline,
                parser,
                calculator,
                config,
                classements
            )

        print()

    def _process_csv(
        self,
        csv_path: str,
        course_name: str,
        discipline: str,
        parser: FFCCSVParser,
        calculator: PointsCalculator,
        config: Config,
        classements: Dict[str, CoureurClassement]
    ) -> None:
        """Traite un CSV FFC"""
        # Parser le CSV
        resultats = parser.parse_course_csv(csv_path)
        if not resultats:
            return

        # Récupérer les métadonnées de la course
        metadata = config.get_course_metadata(course_name, discipline)
        
        # Si pas de métadonnées, créer des métadonnées par défaut pour FFC
        if metadata is None:
            print(f"   ℹ️  Création automatique des métadonnées pour {course_name} (FFC)")
            metadata = CourseMetadata(
                nom=course_name,
                discipline=discipline,
                federation="ffc",  # FFC par défaut pour les CSV
                is_objectif=False,
                saison="25-26"
            )
        
        federation = metadata.federation
        is_objectif = metadata.is_objectif
        
        print(f"   DEBUG: discipline={discipline}, federation={federation}")

        # Affichage
        objectif_marker = " ⭐" if is_objectif else ""
        nb_coureurs_trouves = 0

        # Pour chaque coureur ECWM
        for coureur in config.coureurs:
            # Vérifier si autorisé pour cette discipline
            if not config.coureur_autorise(coureur, discipline, federation):
                continue

            nom_norm = utils.normalize_name(coureur)

            # Chercher le coureur dans les résultats
            resultat = parser.find_coureur_in_results(nom_norm, resultats)

            if resultat:
                nb_coureurs_trouves += 1

                # Calculer les points (même méthode que pour les PDFs)
                course_points = calculator.calculate_course_points(
                    coureur=coureur,
                    course_name=course_name,
                    resultat=resultat,
                    discipline=discipline,
                    course_metadata=metadata
                )

                # Ajouter au classement
                classements[nom_norm].add_course(course_points)

        # Affichage
        course_display = course_name.upper().ljust(25)
        print(f"📄 {course_display}→ {nb_coureurs_trouves:2d} coureurs{objectif_marker}")


    def _process_manual_entries(
        self,
        manual_parser: ManualParser,
        calculator: PointsCalculator,
        config: Config,
        classements: Dict[str, CoureurClassement]
    ) -> None:
        """Traite les saisies manuelles"""
        manual_results = manual_parser.load_all_sources()

        if not manual_results:
            return

        nb_resultats = 0
        for result in manual_results:
            # Chercher le coureur parmi nos coureurs ECWM
            coureur_trouve = None
            for coureur in config.coureurs:
                if utils.normalize_name(coureur) == result.coureur:
                    coureur_trouve = coureur
                    break

            if not coureur_trouve:
                continue

            # Récupérer les métadonnées (ou créer avec les infos du result)
            manual_metadata = config.get_course_metadata(result.course_name, result.discipline)

            # Si pas de métadonnées, créer avec les infos de la saisie manuelle
            if manual_metadata is None:
                from src.core.models import CourseMetadata
                manual_metadata = CourseMetadata(
                    nom=result.course_name,
                    discipline=result.discipline,
                    federation=result.federation,  # Utiliser la fédération de la saisie manuelle !
                    is_objectif=False,
                    saison="25-26"
                )

            # Calculer les points (utiliser la méthode pour saisies manuelles)
            course_points = calculator.calculate_course_points_manual(
                coureur=coureur_trouve,
                course_name=result.course_name,
                position=result.position,
                nb_participants=result.nb_participants,
                categorie=result.categorie or "Saisie manuelle",
                discipline=result.discipline,
                course_metadata=manual_metadata
            )

            # Ajouter au classement
            nom_norm = utils.normalize_name(coureur_trouve)
            classements[nom_norm].add_course(course_points)
            nb_resultats += 1

        print(f"   ✅ {nb_resultats} résultats manuels traités")
        print()

    def _print_top10(self, classements: Dict[str, CoureurClassement]) -> None:
        """Affiche le TOP 10"""
        print("\n🏆 TOP 10 du classement")
        print("=" * 70)

        # Trier par points
        classement_sorted = sorted(
            classements.values(),
            key=lambda x: x.points_total,
            reverse=True
        )

        # Afficher le TOP 10
        for i, coureur in enumerate(classement_sorted[:10], 1):
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            else:
                medal = f"{i:2d}. "

            nom_display = coureur.nom.ljust(25)
            points_display = f"{coureur.points_total:3d} pts"

            print(f"{medal}{nom_display} {points_display}")
            print(f"    {coureur.nb_courses} courses • {coureur.points_courses} pts courses")

        print("\n✅ Terminé !")
        print("=" * 70)

    def step1_extract(self, force: bool = False) -> Dict:
        """
        Étape 1: Extraction des PDFs + saisies manuelles

        Args:
            force: Forcer la réextraction même si le cache est valide

        Returns:
            Dictionnaire des classements
        """
        print("\n" + "=" * 70)
        print("📂 ÉTAPE 1/4 : EXTRACTION DES DONNÉES")
        print("=" * 70)

        # Vérifier le cache
        if not force and self._is_cache_valid(self.extraction_cache):
            print("✅ Cache valide trouvé, chargement depuis le cache...")
            with open(self.extraction_cache, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            print(f"   📦 {len(cached_data)} coureurs chargés depuis le cache")
            print()
            return cached_data

        print("🔄 Extraction des données...")
        print()

        # Exécuter l'extraction complète
        classements = self._run_extraction()

        # Sérialiser les classements pour le cache
        classements_data = {}
        for nom, coureur in classements.items():
            classements_data[nom] = {
                'nom': coureur.nom,
                'courses_detail': [
                    {
                        'coureur': cp.coureur,
                        'course': cp.course,
                        'position': cp.position,
                        'nb_participants': cp.nb_participants,
                        'categorie': cp.categorie,
                        'discipline': cp.discipline,
                        'federation': cp.federation,
                        'percentile': cp.percentile,
                        'points_participation': cp.points_participation,
                        'points_performance': cp.points_performance,
                        'coefficient': cp.coefficient,
                        'bonus_objectif': cp.bonus_objectif,
                        'points_total': cp.points_total,
                    }
                    for cp in coureur.courses_detail
                ],
                'nb_courses': coureur.nb_courses,
                'nb_courses_objectif': coureur.nb_courses_objectif,
                'points_courses': coureur.points_courses,
                'bonus_badges': 0,  # Sera calculé à l'étape 3
                'points_total': coureur.points_total,
            }

        # Sauvegarder le cache
        with open(self.extraction_cache, 'w', encoding='utf-8') as f:
            json.dump(classements_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Cache sauvegardé : {self.extraction_cache}")
        print()

        return classements_data

    def step2_calculate_badges(self, classements_data: Dict) -> Dict:
        """
        Étape 2: Calcul des badges et bonus

        Args:
            classements_data: Données des classements

        Returns:
            Dictionnaire des badges par coureur
        """
        print("\n" + "=" * 70)
        print("🏅 ÉTAPE 2/4 : CALCUL DES BADGES")
        print("=" * 70)

        from src.core.config import Config
        from src.core.models import CoureurPoints

        # Charger la configuration
        config = Config()

        # Reconstruire les objets CoureurClassement depuis le JSON
        classements_objets = {}
        for nom, data in classements_data.items():
            coureur = CoureurClassement(nom=data['nom'])
            coureur.courses_detail = [
                CoureurPoints(**cp) for cp in data['courses_detail']
            ]
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
                coureur,
                courses_metadata_dict,
                total_courses_saison
            )
            bonus_total = sum(badge.bonus_points for badge in badges_obtenus)

            badges_par_coureur[nom_norm] = {
                'bonus_total': bonus_total,
                'badges_obtenus': [
                    {
                        'badge_id': b.badge_id,
                        'nom': b.nom,
                        'emoji': b.emoji,
                        'description': b.description,
                        'niveau': b.niveau,
                        'valeur_obtenue': b.valeur_obtenue,
                        'bonus_points': b.bonus_points,
                    }
                    for b in badges_obtenus
                ]
            }

            # Mettre à jour les totaux dans classements_data
            classements_data[nom_norm]['bonus_badges'] = bonus_total
            classements_data[nom_norm]['points_total'] = (
                classements_data[nom_norm]['points_courses'] + bonus_total
            )

        # Sauvegarder le cache des badges
        with open(self.badges_cache, 'w', encoding='utf-8') as f:
            json.dump(badges_par_coureur, f, indent=2, ensure_ascii=False)

        print(f"💾 Badges sauvegardés : {self.badges_cache}")
        print(f"   🏅 {len(badges_par_coureur)} coureurs avec badges calculés")
        print()

        return badges_par_coureur

    def step3_generate_csv(self, classements_data: Dict) -> None:
        """
        Étape 3: Génération du CSV classement

        Args:
            classements_data: Données des classements avec badges
        """
        print("\n" + "=" * 70)
        print("💾 ÉTAPE 3/4 : GÉNÉRATION DU CSV CLASSEMENT")
        print("=" * 70)

        import pandas as pd

        # Préparer les données pour le CSV
        rows = []
        for nom, coureur_data in classements_data.items():
            # Ligne par course
            for course in coureur_data['courses_detail']:
                rows.append({
                    'Coureur': coureur_data['nom'],
                    'Course': course['course'],
                    'Position': course['position'],
                    'Nb_Participants': course['nb_participants'],
                    'Catégorie': course['categorie'],
                    'Discipline': course['discipline'],
                    'Fédération': course['federation'],
                    'Percentile': round(course['percentile'], 2),
                    'Points_Participation': round(course['points_participation'], 1),
                    'Points_Performance': round(course['points_performance'], 1),
                    'Coefficient': course['coefficient'],
                    'Bonus_Objectif': course['bonus_objectif'],
                    'Points_Total_Course': round(course['points_total'], 1),
                })

            # Ligne de total
            rows.append({
                'Coureur': coureur_data['nom'],
                'Course': '--- TOTAL ---',
                'Position': '',
                'Nb_Participants': '',
                'Catégorie': '',
                'Discipline': '',
                'Fédération': '',
                'Percentile': '',
                'Points_Participation': '',
                'Points_Performance': '',
                'Coefficient': '',
                'Bonus_Objectif': '',
                'Points_Total_Course': round(coureur_data['points_courses'], 1),
            })

            # Ligne bonus badges
            rows.append({
                'Coureur': coureur_data['nom'],
                'Course': '--- BONUS BADGES ---',
                'Position': '',
                'Nb_Participants': '',
                'Catégorie': '',
                'Discipline': '',
                'Fédération': '',
                'Percentile': '',
                'Points_Participation': '',
                'Points_Performance': '',
                'Coefficient': '',
                'Bonus_Objectif': '',
                'Points_Total_Course': coureur_data['bonus_badges'],
            })

            # Ligne de grand total
            rows.append({
                'Coureur': coureur_data['nom'],
                'Course': '========== TOTAL GÉNÉRAL ==========',
                'Position': '',
                'Nb_Participants': '',
                'Catégorie': '',
                'Discipline': '',
                'Fédération': '',
                'Percentile': '',
                'Points_Participation': '',
                'Points_Performance': '',
                'Coefficient': '',
                'Bonus_Objectif': '',
                'Points_Total_Course': round(coureur_data['points_total'], 1),
            })

        # Créer le DataFrame et sauvegarder
        df = pd.DataFrame(rows)
        output_path = "ecwm_classements.csv"
        df.to_csv(output_path, index=False, encoding='utf-8-sig')

        print(f"✅ CSV généré : {output_path}")
        print(f"   📊 {len(classements_data)} coureurs")
        print()

    def step4_generate_site_json(
        self,
        classements_data: Dict,
        badges_data: Dict
    ) -> None:
        """
        Étape 4: Génération du JSON pour le site web

        Args:
            classements_data: Données des classements
            badges_data: Données des badges
        """
        print("\n" + "=" * 70)
        print("🌐 ÉTAPE 4/4 : GÉNÉRATION DU JSON POUR LE SITE")
        print("=" * 70)

        from src.core.config import Config

        # Charger la config
        config = Config()

        # Préparer les données coureurs pour le site
        coureurs_data = []
        for nom, coureur_data in classements_data.items():
            # Récupérer les badges du coureur
            coureur_badges = badges_data.get(nom, {})

            coureur_json = {
                'nom': coureur_data['nom'],
                'nb_courses': coureur_data['nb_courses'],
                'nb_courses_objectif': coureur_data['nb_courses_objectif'],
                'points_courses': round(coureur_data['points_courses'], 1),
                'bonus_badges': coureur_data['bonus_badges'],
                'points_total': round(coureur_data['points_total'], 1),
                'courses_detail': [  # Renommé de 'courses' → 'courses_detail'
                    {
                        'course': cp['course'],
                        'position': cp['position'],
                        'nb_participants': cp['nb_participants'],
                        'categorie': cp['categorie'],
                        'discipline': cp['discipline'],
                        'federation': cp['federation'],
                        'percentile': round(cp['percentile'] * 100, 1),  # Convertir en pourcentage
                        'points_participation': round(cp['points_participation'], 1),
                        'points_performance': round(cp['points_performance'], 1),
                        'coefficient': cp['coefficient'],
                        'bonus_objectif': cp['bonus_objectif'],
                        'points': round(cp['points_total'], 1),
                    }
                    for cp in coureur_data['courses_detail']
                ],
                'badges': [
                    {
                        'badge_id': badge['badge_id'],
                        'nom': badge['nom'],
                        'emoji': badge['emoji'],
                        'description': badge['description'],
                        'niveau': badge['niveau'],
                        'valeur_obtenue': badge['valeur_obtenue'],
                        'bonus_points': badge['bonus_points'],
                    }
                    for badge in coureur_badges.get('badges_obtenus', [])
                ]
            }
            coureurs_data.append(coureur_json)

        # Trier par points total décroissant
        coureurs_data.sort(key=lambda c: c['points_total'], reverse=True)

        # Ajouter le rang
        for i, coureur in enumerate(coureurs_data, 1):
            coureur['rang'] = i

        # Calculer la liste des courses avec participants
        # Utiliser (nom, discipline, federation) comme clé pour séparer UFOLEP et FFC
        courses_stats = {}  # {(nom, discipline, federation): {nb_participants, is_objectif}}
        for coureur_data in classements_data.values():
            for cp in coureur_data['courses_detail']:
                key = (cp['course'], cp['discipline'], cp['federation'])
                if key not in courses_stats:
                    # Récupérer les métadonnées de la course
                    metadata = config.get_course_metadata(cp['course'], cp['discipline'])
                    courses_stats[key] = {
                        'nb_participants': 0,
                        'is_objectif': metadata.is_objectif if metadata else False
                    }
                courses_stats[key]['nb_participants'] += 1

        # Construire la liste des courses pour le site
        courses_list = []
        for (nom, discipline, federation), stats in courses_stats.items():
            courses_list.append({
                'nom': nom,
                'discipline': discipline,
                'federation': federation,
                'is_objectif': stats['is_objectif'],
                'nb_participants': stats['nb_participants']
            })

        # Trier par nom
        courses_list.sort(key=lambda c: c['nom'])

        # Charger la configuration des badges pour le site
        badge_calculator = BadgeCalculator()
        badges_config_list = []
        for badge in badge_calculator.badges:
            badges_config_list.append({
                'badge_id': badge.badge_id,
                'nom': badge.nom,
                'emoji': badge.emoji,
                'description': badge.description,
                'type': badge.type,
                'critere': badge.critere,
                'niveau': badge.niveau,
                'seuil': badge.seuil,
                'bonus_points': badge.bonus_points,
                'actif': badge.actif
            })

        # Construire le JSON final (compatible avec app.js)
        site_data = {
            'meta': {
                'derniere_maj': datetime.now().strftime('%d/%m/%Y à %H:%M'),
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

        # Sauvegarder
        output_path = "docs/data.json"
        os.makedirs("docs", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(site_data, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON généré : {output_path}")
        print(f"   🏆 Classement de {len(coureurs_data)} coureurs")
        print()

    def run_full_pipeline(self, force_extract: bool = False) -> None:
        """
        Exécute le workflow complet

        Args:
            force_extract: Forcer la réextraction même si le cache est valide
        """
        print("\n")
        print("╔═══════════════════════════════════════════════════════════════════╗")
        print("║                 ECWM CHALLENGE - PIPELINE COMPLET                  ║")
        print("╚═══════════════════════════════════════════════════════════════════╝")

        # Étape 1: Extraction
        classements_data = self.step1_extract(force=force_extract)

        # Étape 2: Badges
        badges_data = self.step2_calculate_badges(classements_data)

        # Étape 3: CSV
        self.step3_generate_csv(classements_data)

        # Étape 4: Site JSON
        self.step4_generate_site_json(classements_data, badges_data)

        print("\n" + "=" * 70)
        print("✅ PIPELINE TERMINÉ AVEC SUCCÈS!")
        print("=" * 70)
        print()
        print("📁 Fichiers générés :")
        print("   • ecwm_classements.csv  → Classement complet (CSV)")
        print("   • docs/data.json        → Données pour le site web")
        print()
        print("🚀 Pour lancer le serveur local :")
        print("   python3 serve.py")
        print()


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description='ECWM Challenge - Pipeline complet d\'extraction et génération',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python3 main.py                    # Workflow complet avec cache intelligent
  python3 main.py --skip-cache       # Forcer la réextraction des PDFs
  python3 main.py --extract-only     # Extraction uniquement (créer le cache)
  python3 main.py --generate-only    # Génération site uniquement (utiliser le cache)
        """
    )

    parser.add_argument(
        '--skip-cache',
        action='store_true',
        help='Forcer la réextraction des PDFs (ignorer le cache)'
    )

    parser.add_argument(
        '--extract-only',
        action='store_true',
        help='Extraction uniquement (ne pas générer le site)'
    )

    parser.add_argument(
        '--generate-only',
        action='store_true',
        help='Génération du site uniquement (utiliser le cache)'
    )

    args = parser.parse_args()

    # Créer le pipeline
    pipeline = ECWMPipeline()

    if args.extract_only:
        # Extraction seule
        classements_data = pipeline.step1_extract(force=args.skip_cache)
        badges_data = pipeline.step2_calculate_badges(classements_data)
        print("✅ Extraction terminée (cache créé)")

    elif args.generate_only:
        # Génération seule (depuis le cache)
        if not pipeline.extraction_cache.exists():
            print("❌ Erreur: Pas de cache trouvé. Exécutez d'abord l'extraction.")
            sys.exit(1)

        with open(pipeline.extraction_cache, 'r', encoding='utf-8') as f:
            classements_data = json.load(f)

        badges_data = pipeline.step2_calculate_badges(classements_data)
        pipeline.step3_generate_csv(classements_data)
        pipeline.step4_generate_site_json(classements_data, badges_data)

    else:
        # Pipeline complet
        pipeline.run_full_pipeline(force_extract=args.skip_cache)


if __name__ == "__main__":
    main()
