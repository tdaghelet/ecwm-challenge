#!/usr/bin/env python3
"""
Extracteur de résultats FFC depuis les pages web

Parse les URLs FFC configurées dans data/ffc_sources.csv
et génère un CSV par course dans classements/ffc/{saison}/

Usage:
    python3 extract_ffc.py              # Parse uniquement les nouvelles URLs
    python3 extract_ffc.py --force-extract  # Re-parse toutes les URLs
"""
import argparse
import os
import re
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Mapping des mois français vers numéros
MOIS_FR = {
    'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
    'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
    'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12',
    # Variantes sans accent
    'fevrier': '02', 'aout': '08'
}


@dataclass
class FFCResult:
    """Résultat d'un coureur FFC"""
    coureur: str  # Format: "NOM PRENOM"
    position: str
    nb_participants: int
    categorie: str
    date_course: Optional[str] = None  # Format YYYY-MM-DD


class FFCExtractor:
    """Extracteur de résultats depuis les pages FFC"""

    def __init__(self, sources_file: str = "data/ffc_sources.csv",
                 base_output_dir: str = "classements/ffc"):
        """
        Initialise l'extracteur

        Args:
            sources_file: Fichier CSV contenant les URLs à parser
            base_output_dir: Répertoire de base pour les CSV de sortie
        """
        self.sources_file = sources_file
        self.base_output_dir = Path(base_output_dir)

    def _parse_date_fr(self, date_str: str) -> Optional[str]:
        """
        Parse une date française en format YYYY-MM-DD

        Args:
            date_str: Date au format "29 novembre 2025" ou "29/11/2025"

        Returns:
            Date au format YYYY-MM-DD ou None si parsing impossible
        """
        if not date_str:
            return None

        date_str = date_str.strip().lower()

        # Format numérique: "29/11/2025" ou "29-11-2025"
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
        if match:
            jour, mois, annee = match.groups()
            if len(annee) == 2:
                annee = '20' + annee
            return f"{annee}-{mois.zfill(2)}-{jour.zfill(2)}"

        # Format textuel: "29 novembre 2025"
        match = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
        if match:
            jour, mois_str, annee = match.groups()
            mois = MOIS_FR.get(mois_str)
            if mois:
                return f"{annee}-{mois}-{jour.zfill(2)}"

        return None

    def _extract_date_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extrait la date depuis une page de résultats FFC

        Args:
            soup: BeautifulSoup de la page

        Returns:
            Date au format YYYY-MM-DD ou None
        """
        # Chercher dans les éléments typiques (h1, h2, header, etc.)
        for selector in ['h1', 'h2', '.date', '.event-date', 'header', '.race-info']:
            elements = soup.select(selector) if '.' in selector else soup.find_all(selector)
            for element in elements:
                text = element.get_text()
                # Pattern: "29 novembre 2025" ou similaire
                match = re.search(r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre)\s+(\d{4})', text, re.IGNORECASE)
                if match:
                    jour, mois_str, annee = match.groups()
                    mois = MOIS_FR.get(mois_str.lower())
                    if mois:
                        return f"{annee}-{mois}-{jour.zfill(2)}"

        # Chercher dans le texte complet de la page
        page_text = soup.get_text()
        match = re.search(r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre)\s+(\d{4})', page_text, re.IGNORECASE)
        if match:
            jour, mois_str, annee = match.groups()
            mois = MOIS_FR.get(mois_str.lower())
            if mois:
                return f"{annee}-{mois}-{jour.zfill(2)}"

        return None
        
    def load_sources(self) -> pd.DataFrame:
        """Charge les sources depuis le fichier CSV"""
        if not os.path.exists(self.sources_file):
            print(f"Fichier {self.sources_file} introuvable")
            sys.exit(1)

        df = pd.read_csv(self.sources_file, comment='#')
        # La colonne date n'est plus obligatoire (sera extraite depuis la page)
        required_cols = ['course_name', 'discipline', 'saison', 'url']

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"Colonnes manquantes dans {self.sources_file}: {missing}")
            sys.exit(1)

        return df
    
    def get_output_path(self, course_name: str, saison: str) -> Path:
        """
        Détermine le chemin du fichier CSV de sortie
        
        Args:
            course_name: Nom de la course
            saison: Saison (ex: cx-25-26)
            
        Returns:
            Path du fichier CSV
        """
        output_dir = self.base_output_dir / saison
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{course_name}.csv"
    
    def parse_ffc_page(self, url: str) -> tuple[List[FFCResult], Optional[str]]:
        """
        Parse une page de résultats FFC

        Args:
            url: URL de la page FFC

        Returns:
            Tuple (liste des résultats, date extraite au format YYYY-MM-DD)
        """
        try:
            # Récupérer la page
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extraire la date de la course
            date_course = self._extract_date_from_page(soup)

            # Trouver tous les tableaux
            tables = soup.find_all('table')

            if not tables:
                return [], date_course

            results = []

            # Parser chaque tableau (une catégorie par tableau)
            for table in tables:
                # Trouver l'en-tête de catégorie (h2 ou h3 avant le tableau)
                categorie = "Unknown"
                prev_element = table.find_previous(['h2', 'h3', 'h4'])
                if prev_element:
                    categorie = prev_element.text.strip()

                # Parser les lignes du tableau
                rows = table.find_all('tr')

                # Ignorer la première ligne (en-têtes)
                data_rows = rows[1:]

                if not data_rows:
                    continue

                # Le nombre de participants = dernière position
                nb_participants = len(data_rows)

                for row in data_rows:
                    cols = row.find_all('td')

                    if len(cols) < 4:  # Minimum: Rang, Nom, Prénom, ...
                        continue

                    # Extraire les données
                    position = cols[0].text.strip()

                    # Ignorer les lignes sans position valide
                    if not position or not position.isdigit():
                        continue

                    # UCIID = cols[1] (on ne l'utilise pas pour l'instant)
                    nom = cols[2].text.strip().upper()
                    prenom = cols[3].text.strip().upper()

                    # Format coureur : "NOM PRENOM"
                    coureur = f"{nom} {prenom}"

                    result = FFCResult(
                        coureur=coureur,
                        position=position,
                        nb_participants=nb_participants,
                        categorie=categorie,
                        date_course=date_course
                    )
                    results.append(result)

            return results, date_course

        except requests.RequestException as e:
            print(f"Erreur HTTP: {e}")
            return [], None
        except Exception as e:
            print(f"Erreur: {e}")
            return [], None
    
    def save_course_csv(
        self,
        results: List[FFCResult],
        course_name: str,
        saison: str,
        date_course: Optional[str] = None
    ) -> None:
        """
        Sauvegarde les résultats d'une course dans un CSV

        Args:
            results: Liste des résultats
            course_name: Nom de la course
            saison: Saison (ex: cx-25-26)
            date_course: Date de la course au format YYYY-MM-DD
        """
        if not results:
            return

        # Convertir en DataFrame
        data = []
        for result in results:
            data.append({
                'coureur': result.coureur,
                'position': result.position,
                'nb_participants': result.nb_participants,
                'categorie': result.categorie,
                'date_course': date_course or result.date_course or ''
            })

        df = pd.DataFrame(data)

        # Déterminer le chemin de sortie
        output_path = self.get_output_path(course_name, saison)

        # Sauvegarder avec en-tête commenté
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Course FFC: {course_name}\n")
            f.write(f"# Saison: {saison}\n")
            if date_course:
                f.write(f"# Date: {date_course}\n")
            f.write(f"# Nombre total de résultats: {len(results)}\n")

        df.to_csv(output_path, index=False, mode='a')

    def update_courses_metadata(
        self,
        courses_info: list,
        metadata_path: str = "data/courses_metadata.csv"
    ) -> int:
        """
        Met à jour courses_metadata.csv avec les courses FFC :
        - Ajoute les nouvelles courses
        - Met à jour les dates des courses existantes

        Args:
            courses_info: Liste de dicts {course_name, discipline, saison, date_course}
            metadata_path: Chemin du fichier CSV de métadonnées

        Returns:
            Nombre de courses ajoutées ou mises à jour
        """
        import csv

        # Lire le fichier existant (ou créer un fichier vide)
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

        # Index des courses existantes par (nom, discipline)
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
            saison = info.get('saison', '25-26')

            key = (course_name, discipline)

            if key in existing_courses:
                # Course existe -> mettre à jour la date si différente
                idx = existing_courses[key]
                old_date = rows[idx].get('date_course', '')
                if date_course and date_course != old_date:
                    rows[idx]['date_course'] = date_course
                    updated += 1
            else:
                # Nouvelle course -> ajouter
                new_row = {
                    'nom': course_name,
                    'discipline': discipline,
                    'federation': 'ffc',
                    'is_objectif': 'false',
                    'saison': saison.replace('cx-', '').replace('route-', ''),
                    'date_course': date_course
                }
                rows.append(new_row)
                existing_courses[key] = len(rows) - 1
                added += 1

        # Trier par nom puis discipline
        rows.sort(key=lambda r: (r['nom'].lower(), r['discipline'].lower()))

        # Écrire le fichier
        with open(metadata_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"   {added} courses ajoutées, {updated} dates mises à jour dans {metadata_path}")
        return added + updated

    def run(self, force_extract: bool = False) -> None:
        """
        Exécute l'extraction
        
        Args:
            force_extract: Si True, re-parse toutes les URLs
        """
        print("🏁 Extraction des résultats FFC")
        print("=" * 70)
        print()
        
        # Charger les sources
        df_sources = self.load_sources()
        print(f"📋 {len(df_sources)} URLs configurées")
        
        # Grouper par course_name (plusieurs URLs peuvent pointer vers la même course)
        courses_grouped = df_sources.groupby('course_name')
        print(f"   {len(courses_grouped)} courses uniques")
        print()
        
        print("Extraction en cours...")
        print("-" * 70)

        new_count = 0
        skipped_count = 0
        error_count = 0
        courses_info = []  # Pour mise à jour du metadata

        for course_name, group in courses_grouped:
            # Prendre les infos de la première ligne du groupe
            first_row = group.iloc[0]
            saison = first_row['saison']
            discipline = first_row['discipline']

            # Vérifier si le fichier existe déjà
            output_path = self.get_output_path(course_name, saison)

            if output_path.exists() and not force_extract:
                # Lire la date depuis le fichier existant pour le metadata
                try:
                    existing_df = pd.read_csv(output_path, comment='#')
                    if 'date_course' in existing_df.columns and len(existing_df) > 0:
                        existing_date = existing_df['date_course'].iloc[0]
                        if pd.notna(existing_date):
                            courses_info.append({
                                'course_name': course_name,
                                'discipline': discipline,
                                'saison': saison,
                                'date_course': str(existing_date)
                            })
                except:
                    pass
                print(f"   {course_name:20s} (deja extrait)")
                skipped_count += 1
                continue

            # Parser toutes les URLs de cette course et agréger les résultats
            print(f"   {course_name:20s} ({len(group)} URLs) ", end="")
            all_results = []
            date_course = None

            for _, source in group.iterrows():
                url = source['url']
                results, extracted_date = self.parse_ffc_page(url)
                if results:
                    all_results.extend(results)
                # Garder la première date trouvée
                if extracted_date and not date_course:
                    date_course = extracted_date

            if all_results:
                # Sauvegarder le CSV avec tous les résultats agrégés
                self.save_course_csv(all_results, course_name, saison, date_course)
                date_info = f" [{date_course}]" if date_course else ""
                print(f"{len(all_results)} resultats{date_info}")
                new_count += 1

                # Ajouter aux infos pour metadata
                courses_info.append({
                    'course_name': course_name,
                    'discipline': discipline,
                    'saison': saison,
                    'date_course': date_course
                })
            else:
                print("Aucun resultat")
                error_count += 1

        print()

        # Mise à jour du fichier courses_metadata.csv
        if courses_info:
            print("Mise a jour des metadonnees...")
            self.update_courses_metadata(courses_info)
            print()

        # Résumé
        print("Resume")
        print("-" * 70)
        print(f"   {new_count} nouvelles courses extraites")
        print(f"   {skipped_count} courses deja en cache")
        if error_count > 0:
            print(f"   {error_count} erreurs")
        print(f"   Fichiers dans: {self.base_output_dir}/")
        print()
        print("Termine !")
        print("=" * 70)


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Extracteur de résultats FFC depuis les pages web"
    )
    parser.add_argument(
        '--force-extract',
        action='store_true',
        help="Re-parse toutes les URLs (ignore le cache)"
    )
    parser.add_argument(
        '--sources',
        default='data/ffc_sources.csv',
        help="Fichier CSV des sources (défaut: data/ffc_sources.csv)"
    )
    parser.add_argument(
        '--output-dir',
        default='classements/ffc',
        help="Répertoire de base pour les CSV (défaut: classements/ffc)"
    )
    
    args = parser.parse_args()
    
    extractor = FFCExtractor(
        sources_file=args.sources,
        base_output_dir=args.output_dir
    )
    
    extractor.run(force_extract=args.force_extract)


if __name__ == "__main__":
    main()
