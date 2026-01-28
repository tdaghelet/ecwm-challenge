"""
Scraper pour le calendrier UFOLEP

Récupère les dates et URLs des PDFs depuis :
- https://www.cyclismeufolep5962.fr/calResCross.php
- https://www.cyclismeufolep5962.fr/calResVTT.php

Permet de télécharger automatiquement les PDFs et mettre à jour courses_metadata.csv
"""
import os
import re
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
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
class UfolepCalendarEntry:
    """Entrée du calendrier UFOLEP"""
    date: str           # Format YYYY-MM-DD
    lieu: str           # Nom normalisé (lowercase)
    organisateur: str   # Nom du club organisateur
    pdf_url: Optional[str]  # URL du PDF des résultats (None si pas encore disponible)
    discipline: str     # "cx" ou "vtt"


class UfolepCalendarScraper:
    """Scraper pour le calendrier UFOLEP CX/VTT"""

    BASE_URL = "https://www.cyclismeufolep5962.fr/"
    CALENDAR_URLS = {
        'cx': "https://www.cyclismeufolep5962.fr/calResCross.php",
        'vtt': "https://www.cyclismeufolep5962.fr/calResVTT.php"
    }

    def __init__(self, timeout: int = 10):
        """
        Initialise le scraper

        Args:
            timeout: Timeout des requêtes HTTP en secondes
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False  # Pour ignorer les erreurs SSL

    def _parse_date_fr(self, date_str: str, year_hint: int = None) -> Optional[str]:
        """
        Parse une date française en format YYYY-MM-DD

        Args:
            date_str: Date au format "17 novembre" ou "17/11/2025"
            year_hint: Année à utiliser si non spécifiée

        Returns:
            Date au format YYYY-MM-DD ou None si parsing impossible
        """
        if not date_str:
            return None

        date_str = date_str.strip().lower()

        # Format numérique: "17/11/2025" ou "17/11/25"
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
        if match:
            jour, mois, annee = match.groups()
            if len(annee) == 2:
                annee = '20' + annee
            return f"{annee}-{mois.zfill(2)}-{jour.zfill(2)}"

        # Format textuel: "17 novembre 2025" ou "17 novembre"
        match = re.match(r'(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?', date_str)
        if match:
            jour, mois_str, annee = match.groups()
            mois = MOIS_FR.get(mois_str)
            if mois:
                if not annee:
                    annee = str(year_hint) if year_hint else str(datetime.now().year)
                return f"{annee}-{mois}-{jour.zfill(2)}"

        return None

    def _normalize_lieu(self, lieu: str) -> str:
        """
        Normalise le nom du lieu

        Args:
            lieu: Nom du lieu brut

        Returns:
            Nom normalisé (lowercase, sans accents problématiques)
        """
        if not lieu:
            return ""

        # Lowercase et strip
        lieu = lieu.strip().lower()

        # Remplacer les espaces par des tirets
        lieu = re.sub(r'\s+', '-', lieu)

        # Supprimer les caractères non alphanumériques (sauf tirets)
        lieu = re.sub(r'[^a-z0-9\-àâäéèêëïîôùûüç]', '', lieu)

        return lieu

    def scrape_calendar(self, discipline: str) -> List[UfolepCalendarEntry]:
        """
        Scrape le calendrier pour une discipline

        Args:
            discipline: "cx" ou "vtt"

        Returns:
            Liste des entrées du calendrier
        """
        if discipline not in self.CALENDAR_URLS:
            raise ValueError(f"Discipline inconnue: {discipline}")

        url = self.CALENDAR_URLS[discipline]
        print(f"   Récupération du calendrier {discipline.upper()}: {url}")

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'

            soup = BeautifulSoup(response.content, 'html.parser')
            entries = []

            # Trouver le tableau des résultats
            # Structure typique: table avec colonnes Date, Lieu, Organisateur, Résultats
            tables = soup.find_all('table')

            for table in tables:
                rows = table.find_all('tr')

                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) < 3:
                        continue

                    # Extraire les données
                    date_text = cols[0].get_text(strip=True)
                    lieu_text = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                    organisateur_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""

                    # Chercher le lien PDF dans la dernière colonne
                    pdf_url = None
                    for col in cols:
                        links = col.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if '.pdf' in href.lower():
                                pdf_url = urljoin(self.BASE_URL, href)
                                break

                    # Parser la date
                    # Déterminer l'année selon la saison (CX = oct-fév, VTT = mars-sept)
                    now = datetime.now()
                    year_hint = now.year
                    # Pour la saison 25-26, utiliser 2025 pour oct-déc, 2026 pour jan-fév
                    date = self._parse_date_fr(date_text, year_hint)

                    # Ignorer les lignes sans date valide ou qui sont des en-têtes
                    if not date or 'date' in date_text.lower():
                        continue

                    lieu = self._normalize_lieu(lieu_text)
                    if not lieu:
                        continue

                    entry = UfolepCalendarEntry(
                        date=date,
                        lieu=lieu,
                        organisateur=organisateur_text,
                        pdf_url=pdf_url,
                        discipline=discipline
                    )
                    entries.append(entry)

            print(f"   {len(entries)} courses trouvées")
            return entries

        except requests.RequestException as e:
            print(f"   Erreur HTTP: {e}")
            return []
        except Exception as e:
            print(f"   Erreur: {e}")
            return []

    def download_pdf(self, pdf_url: str, output_path: str) -> bool:
        """
        Télécharge un PDF

        Args:
            pdf_url: URL du PDF
            output_path: Chemin de destination

        Returns:
            True si téléchargement réussi
        """
        try:
            response = self.session.get(pdf_url, timeout=self.timeout)
            response.raise_for_status()

            # Créer le dossier parent si nécessaire
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            return True

        except Exception as e:
            print(f"   Erreur téléchargement {pdf_url}: {e}")
            return False

    def download_pdfs(
        self,
        entries: List[UfolepCalendarEntry],
        output_dir: str,
        force: bool = False
    ) -> Dict[str, str]:
        """
        Télécharge les PDFs pour les entrées du calendrier

        Args:
            entries: Liste des entrées du calendrier
            output_dir: Répertoire de destination (ex: classements/ufolep/cx-25-26)
            force: Si True, retélécharge même si le fichier existe

        Returns:
            Dictionnaire {lieu: chemin_pdf} des PDFs téléchargés
        """
        downloaded = {}
        skipped = 0
        errors = 0

        for entry in entries:
            if not entry.pdf_url:
                continue

            # Nom du fichier: lieu.pdf
            output_path = os.path.join(output_dir, f"{entry.lieu}.pdf")

            if os.path.exists(output_path) and not force:
                skipped += 1
                downloaded[entry.lieu] = output_path
                continue

            print(f"   Téléchargement: {entry.lieu} ({entry.date})")
            if self.download_pdf(entry.pdf_url, output_path):
                downloaded[entry.lieu] = output_path
            else:
                errors += 1

        print(f"   {len(downloaded)} PDFs téléchargés, {skipped} ignorés, {errors} erreurs")
        return downloaded

    def update_courses_metadata(
        self,
        entries: List[UfolepCalendarEntry],
        metadata_path: str = "data/courses_metadata.csv"
    ) -> int:
        """
        Met à jour courses_metadata.csv avec les courses scrapées :
        - Ajoute les nouvelles courses
        - Met à jour les dates des courses existantes

        Args:
            entries: Liste des entrées du calendrier
            metadata_path: Chemin du fichier CSV de métadonnées

        Returns:
            Nombre de courses ajoutées ou mises à jour
        """
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

        for entry in entries:
            key = (entry.lieu, entry.discipline)

            if key in existing_courses:
                # Course existe -> mettre à jour la date si différente
                idx = existing_courses[key]
                old_date = rows[idx].get('date_course', '')
                if entry.date and entry.date != old_date:
                    rows[idx]['date_course'] = entry.date
                    updated += 1
            else:
                # Nouvelle course -> ajouter
                new_row = {
                    'nom': entry.lieu,
                    'discipline': entry.discipline,
                    'federation': 'ufolep',
                    'is_objectif': 'false',
                    'saison': '25-26',
                    'date_course': entry.date or ''
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

    def run_full_sync(
        self,
        output_base_dir: str = "classements/ufolep",
        saison: str = "25-26",
        force_download: bool = False,
        dry_run: bool = False
    ) -> Dict[str, List[UfolepCalendarEntry]]:
        """
        Synchronisation complète: scrape + téléchargement + mise à jour metadata

        Args:
            output_base_dir: Répertoire de base pour les PDFs
            saison: Identifiant de la saison (ex: "25-26")
            force_download: Si True, retélécharge tous les PDFs
            dry_run: Si True, n'effectue aucune écriture

        Returns:
            Dictionnaire {discipline: entries} avec toutes les entrées trouvées
        """
        all_entries = {}

        for discipline in ['cx', 'vtt']:
            print(f"\n{'='*60}")
            print(f"UFOLEP {discipline.upper()} - Saison {saison}")
            print('='*60)

            # Scraper le calendrier
            entries = self.scrape_calendar(discipline)
            all_entries[discipline] = entries

            if dry_run:
                print("\n   [DRY RUN] Actions qui seraient effectuées:")
                for entry in entries:
                    status = "PDF disponible" if entry.pdf_url else "Pas de PDF"
                    print(f"   - {entry.lieu} ({entry.date}): {status}")
                continue

            # Télécharger les PDFs
            if entries:
                output_dir = os.path.join(output_base_dir, f"{discipline}-{saison}")
                self.download_pdfs(entries, output_dir, force=force_download)

        # Mettre à jour les métadonnées (tous les disciplines ensemble)
        if not dry_run:
            all_entries_flat = []
            for entries_list in all_entries.values():
                all_entries_flat.extend(entries_list)

            if all_entries_flat:
                print("\nMise à jour des métadonnées...")
                self.update_courses_metadata(all_entries_flat)

        return all_entries
