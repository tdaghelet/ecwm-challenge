"""
Scraper pour les résultats FFC

Récupère les résultats depuis les pages FFC et les convertit en CSV.
URLs configurées dans config/sources_ffc.csv
"""
import os
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class FFCResult:
    """Résultat d'un coureur FFC"""
    coureur: str
    position: str
    nb_participants: int
    categorie: str
    date_course: Optional[str] = None


class FFCExtractor:
    """Extracteur de résultats depuis les pages FFC"""

    MOIS_FR = {
        'janvier': '01', 'fevrier': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'aout': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'decembre': '12',
        'février': '02', 'août': '08'
    }

    def __init__(self, sources_file: str = "config/sources_ffc.csv",
                 base_output_dir: str = "classements/ffc"):
        self.sources_file = sources_file
        self.base_output_dir = Path(base_output_dir)

    def _parse_date_fr(self, date_str: str) -> Optional[str]:
        """Parse une date française en format YYYY-MM-DD"""
        if not date_str:
            return None

        date_str = date_str.strip().lower()

        # Format numérique
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
        if match:
            jour, mois, annee = match.groups()
            if len(annee) == 2:
                annee = '20' + annee
            return f"{annee}-{mois.zfill(2)}-{jour.zfill(2)}"

        # Format textuel
        match = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
        if match:
            jour, mois_str, annee = match.groups()
            mois = self.MOIS_FR.get(mois_str)
            if mois:
                return f"{annee}-{mois}-{jour.zfill(2)}"

        return None

    def _extract_date_from_page(self, soup) -> Optional[str]:
        """Extrait la date depuis une page de résultats FFC"""
        for selector in ['h1', 'h2', '.date', '.event-date', 'header', '.race-info']:
            elements = soup.select(selector) if '.' in selector else soup.find_all(selector)
            for element in elements:
                text = element.get_text()
                match = re.search(
                    r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre)\s+(\d{4})',
                    text, re.IGNORECASE
                )
                if match:
                    jour, mois_str, annee = match.groups()
                    mois = self.MOIS_FR.get(mois_str.lower())
                    if mois:
                        return f"{annee}-{mois}-{jour.zfill(2)}"

        page_text = soup.get_text()
        match = re.search(
            r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre)\s+(\d{4})',
            page_text, re.IGNORECASE
        )
        if match:
            jour, mois_str, annee = match.groups()
            mois = self.MOIS_FR.get(mois_str.lower())
            if mois:
                return f"{annee}-{mois}-{jour.zfill(2)}"

        return None

    def load_sources(self) -> pd.DataFrame:
        """Charge les sources depuis le fichier CSV"""
        if not os.path.exists(self.sources_file):
            print(f"Fichier {self.sources_file} introuvable")
            return pd.DataFrame()

        df = pd.read_csv(self.sources_file, comment='#')
        required_cols = ['course_name', 'discipline', 'saison', 'url']

        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"Colonnes manquantes dans {self.sources_file}: {missing}")
            return pd.DataFrame()

        return df

    def get_output_path(self, course_name: str, saison: str) -> Path:
        """Détermine le chemin du fichier CSV de sortie"""
        output_dir = self.base_output_dir / saison
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{course_name}.csv"

    def parse_ffc_page(self, url: str) -> tuple:
        """Parse une page de résultats FFC"""
        try:
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            date_course = self._extract_date_from_page(soup)

            tables = soup.find_all('table')
            if not tables:
                return [], date_course

            results = []

            for table in tables:
                categorie = "Unknown"
                prev_element = table.find_previous(['h2', 'h3', 'h4'])
                if prev_element:
                    categorie = prev_element.text.strip()

                rows = table.find_all('tr')
                data_rows = rows[1:]

                if not data_rows:
                    continue

                nb_participants = len(data_rows)

                for row in data_rows:
                    cols = row.find_all('td')
                    if len(cols) < 4:
                        continue

                    position = cols[0].text.strip()
                    if not position or not position.isdigit():
                        continue

                    nom = cols[2].text.strip().upper()
                    prenom = cols[3].text.strip().upper()
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

        except Exception as e:
            print(f"   Erreur: {e}")
            return [], None

    def save_course_csv(self, results: List[FFCResult], course_name: str,
                        saison: str, date_course: Optional[str] = None) -> None:
        """Sauvegarde les résultats d'une course dans un CSV"""
        if not results:
            return

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
        output_path = self.get_output_path(course_name, saison)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Course FFC: {course_name}\n")
            f.write(f"# Saison: {saison}\n")
            if date_course:
                f.write(f"# Date: {date_course}\n")
            f.write(f"# Nombre total de résultats: {len(results)}\n")

        df.to_csv(output_path, index=False, mode='a')

    def update_courses_metadata(self, courses_info: list,
                                 metadata_path: str = "config/courses.csv") -> int:
        """Met à jour courses.csv avec les courses FFC"""
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
            saison = info.get('saison', '25-26')

            key = (course_name, discipline)

            if key in existing_courses:
                idx = existing_courses[key]
                old_date = rows[idx].get('date_course', '')
                if date_course and date_course != old_date:
                    rows[idx]['date_course'] = date_course
                    updated += 1
            else:
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

        rows.sort(key=lambda r: (r['nom'].lower(), r['discipline'].lower()))

        with open(metadata_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        if added > 0 or updated > 0:
            print(f"   {added} courses ajoutées, {updated} dates mises à jour")
        return added + updated

    def run(self, force_extract: bool = False, dry_run: bool = False) -> None:
        """Execute l'extraction FFC"""
        print("\n" + "=" * 70)
        print("SYNCHRONISATION FFC")
        print("=" * 70)

        df_sources = self.load_sources()
        if df_sources.empty:
            print("Aucune source FFC configurée")
            return

        print(f"   {len(df_sources)} URLs configurées")

        courses_grouped = df_sources.groupby('course_name')
        print(f"   {len(courses_grouped)} courses uniques\n")

        if dry_run:
            print("[DRY RUN] Courses qui seraient traitées:")
            for course_name, _ in courses_grouped:
                print(f"   - {course_name}")
            return

        new_count = 0
        skipped_count = 0
        courses_info = []

        for course_name, group in courses_grouped:
            first_row = group.iloc[0]
            saison = first_row['saison']
            discipline = first_row['discipline']

            output_path = self.get_output_path(course_name, saison)

            if output_path.exists() and not force_extract:
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
                except Exception:
                    pass
                print(f"   {course_name:25s} (déjà extrait)")
                skipped_count += 1
                continue

            print(f"   {course_name:25s} ", end="")
            all_results = []
            date_course = None

            for _, source in group.iterrows():
                url = source['url']
                results, extracted_date = self.parse_ffc_page(url)
                if results:
                    all_results.extend(results)
                if extracted_date and not date_course:
                    date_course = extracted_date

            if all_results:
                self.save_course_csv(all_results, course_name, saison, date_course)
                date_info = f" [{date_course}]" if date_course else ""
                print(f"{len(all_results)} résultats{date_info}")
                new_count += 1

                courses_info.append({
                    'course_name': course_name,
                    'discipline': discipline,
                    'saison': saison,
                    'date_course': date_course
                })
            else:
                print("Aucun résultat")

        if courses_info:
            print("\nMise à jour des métadonnées...")
            self.update_courses_metadata(courses_info)

        print(f"\n   {new_count} nouvelles courses, {skipped_count} en cache")
