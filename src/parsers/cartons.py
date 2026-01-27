"""
Parser pour les cartons UFOLEP et licences FFC
Extrait automatiquement la liste des coureurs par discipline/fédération
"""
import re
import pdfplumber
from pathlib import Path
from typing import List, Set
from dataclasses import dataclass

from src.core import utils


@dataclass
class Coureur:
    """Information d'un coureur"""
    nom: str
    prenom: str
    nom_complet: str  # "PRENOM NOM"
    numero_licence: str = ""


class CartonParser:
    """Parser pour les cartons UFOLEP et licences FFC"""

    def __init__(self):
        self.pattern_nom = re.compile(r'^([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ\-\' ]+)\s+([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ\-\' ]+)$')

    def parse_carton_ufolep(self, pdf_path: str) -> List[Coureur]:
        """
        Parse un carton UFOLEP (CX, Route ou VTT)

        Args:
            pdf_path: Chemin vers le PDF du carton

        Returns:
            Liste des coureurs trouvés
        """
        coureurs = []
        coureurs_uniques = set()

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                # Chercher les noms (en majuscules, généralement au début d'une carte)
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()

                    # Les noms sont généralement juste après "Palmares" ou au début
                    # et sont en majuscules complètes
                    if self._is_nom_coureur(line):
                        # Extraire le numéro de licence (quelques lignes plus bas)
                        numero_licence = self._extract_numero_licence(lines[i:i+15])

                        parts = line.split()
                        if len(parts) >= 2:
                            # Dernier mot = nom de famille, reste = prénom
                            nom = parts[-1]
                            prenom = ' '.join(parts[:-1])

                            # Normaliser (supprimer les accents)
                            nom_normalized = utils.normalize_name(nom)
                            prenom_normalized = utils.normalize_name(prenom)
                            nom_complet = f"{prenom_normalized} {nom_normalized}"

                            # Éviter les doublons
                            if nom_complet not in coureurs_uniques:
                                coureurs_uniques.add(nom_complet)
                                coureurs.append(Coureur(
                                    nom=nom_normalized,
                                    prenom=prenom_normalized,
                                    nom_complet=nom_complet,
                                    numero_licence=numero_licence
                                ))

        return coureurs

    def _is_nom_coureur(self, line: str) -> bool:
        """
        Vérifie si une ligne contient un nom de coureur

        Args:
            line: Ligne à vérifier

        Returns:
            True si c'est probablement un nom de coureur
        """
        # Critères:
        # - Tout en majuscules
        # - Au moins 2 mots
        # - Pas de chiffres
        # - Pas de mots-clés comme "Palmares", "Date", etc.

        if not line or len(line) < 5:
            return False

        # Tout en majuscules (avec accents possibles)
        if not line.isupper():
            return False

        # Pas de chiffres
        if any(c.isdigit() for c in line):
            return False

        # Au moins 2 mots
        parts = line.split()
        if len(parts) < 2:
            return False

        # Exclure les mots-clés
        mots_cles = {
            'PALMARES', 'DATE', 'NAISSANCE', 'LICENCE', 'ADULTE', 'JEUNE',
            'MASCULIN', 'FEMININ', 'ESPOIR', 'CYCLISTE', 'WAMBRECHIES',
            'MARQUETTE', 'SURCLASS', 'NON', 'OUI', 'CARTE', 'DELIVREE',
            'HOMOLOGATION', 'PLACE', 'POINT', 'LIEU', 'SSORCOLCYC', 'V . T . T'
        }

        # Si la ligne contient un mot-clé, ce n'est pas un nom
        for mot in parts:
            if mot in mots_cles:
                return False

        # Si la ligne complète est un mot-clé
        if line in mots_cles:
            return False

        # Longueur raisonnable pour un nom
        if len(line) > 50:
            return False

        return True

    def _extract_numero_licence(self, lines: List[str]) -> str:
        """
        Extrait le numéro de licence depuis les lignes suivant le nom

        Args:
            lines: Lignes à scanner

        Returns:
            Numéro de licence ou chaîne vide
        """
        for line in lines:
            # Chercher "N° de Licence :" suivi du numéro
            if 'Licence' in line and ':' in line:
                match = re.search(r':\s*(\d{11,})', line)
                if match:
                    return match.group(1)
        return ""

    def parse_licences_ffc(self, path: str) -> List[Coureur]:
        """
        Parse le fichier des licences FFC (Excel ou PDF)

        Args:
            path: Chemin vers le fichier des licences (Excel ou PDF)

        Returns:
            Liste des coureurs autorisés en compétition
        """
        # Détecter le type de fichier
        if path.endswith('.xlsx') or path.endswith('.xls'):
            return self._parse_licences_ffc_excel(path)
        else:
            return self._parse_licences_ffc_pdf(path)

    def _parse_licences_ffc_excel(self, excel_path: str) -> List[Coureur]:
        """
        Parse le fichier Excel des licences FFC

        Args:
            excel_path: Chemin vers le fichier Excel

        Returns:
            Liste des coureurs compétiteurs
        """
        import pandas as pd

        coureurs = []
        categories_competiteur = ['Elite', 'Open', 'Access', 'U11', 'U13', 'U15', 'U17']

        try:
            # Lire le fichier Excel (en-têtes à la ligne 3)
            df = pd.read_excel(excel_path, header=3)

            for _, row in df.iterrows():
                nom = row.get('Nom')
                prenom = row.get('Prénom')

                if pd.isna(nom):
                    continue

                # Chercher dans les 4 catégories possibles
                is_competitor = False

                for j in range(1, 5):
                    cat_col = f'Catégorie {j}'

                    if cat_col in row and pd.notna(row[cat_col]):
                        cat = str(row[cat_col]).strip()
                        if any(comp_cat in cat for comp_cat in categories_competiteur):
                            is_competitor = True
                            break

                if is_competitor:
                    # Normaliser au format UFOLEP: NOM PRENOM (sans accents, tout en majuscules)
                    # Note: Inversion de l'ordre pour matcher le format UFOLEP
                    prenom_normalized = utils.normalize_name(str(prenom))
                    nom_normalized = utils.normalize_name(str(nom))
                    coureurs.append(Coureur(
                        nom=nom_normalized,
                        prenom=prenom_normalized,
                        nom_complet=f"{nom_normalized} {prenom_normalized}"  # NOM PRENOM
                    ))

        except Exception as e:
            print(f"   ⚠️  Erreur lors de la lecture du fichier Excel: {e}")

        return coureurs

    def _parse_licences_ffc_pdf(self, pdf_path: str) -> List[Coureur]:
        """
        Parse le fichier PDF des licences FFC (fallback)

        Args:
            pdf_path: Chemin vers le PDF des licences

        Returns:
            Liste des coureurs autorisés en compétition
        """
        coureurs = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Essayer d'extraire les tables
                tables = page.extract_tables()

                if tables:
                    for table in tables:
                        coureurs.extend(self._parse_ffc_table(table))
                else:
                    # Fallback: parser le texte brut
                    text = page.extract_text()
                    if text:
                        coureurs.extend(self._parse_ffc_text(text))

        return coureurs

    def _parse_ffc_table(self, table: List[List]) -> List[Coureur]:
        """
        Parse une table FFC

        Args:
            table: Table extraite du PDF

        Returns:
            Liste des coureurs
        """
        coureurs = []

        # Chercher la colonne avec "autorisé en compétition"
        # et la colonne avec les noms
        for row in table:
            if not row:
                continue

            # Chercher "autorisé en compétition" dans la ligne
            autorisation = False
            nom_complet = None

            for cell in row:
                if cell and isinstance(cell, str):
                    if 'autorisé en compétition' in cell.lower():
                        autorisation = True

                    # Potentiellement un nom (en majuscules, 2 mots min)
                    if cell.isupper() and len(cell.split()) >= 2:
                        nom_complet = cell

            if autorisation and nom_complet:
                parts = nom_complet.split()
                if len(parts) >= 2:
                    nom = parts[-1]
                    prenom = ' '.join(parts[:-1])
                    coureurs.append(Coureur(
                        nom=nom,
                        prenom=prenom,
                        nom_complet=f"{prenom} {nom}"
                    ))

        return coureurs

    def _parse_ffc_text(self, text: str) -> List[Coureur]:
        """
        Parse le texte brut FFC en fallback

        Args:
            text: Texte du PDF

        Returns:
            Liste des coureurs
        """
        coureurs = []
        lines = text.split('\n')

        for i, line in enumerate(lines):
            # Chercher "autorisé en compétition"
            if 'autorisé en compétition' in line.lower():
                # Chercher un nom dans les lignes précédentes
                for j in range(max(0, i-5), i):
                    potential_name = lines[j].strip()
                    if self._is_nom_coureur(potential_name):
                        parts = potential_name.split()
                        if len(parts) >= 2:
                            nom = parts[-1]
                            prenom = ' '.join(parts[:-1])
                            coureurs.append(Coureur(
                                nom=nom,
                                prenom=prenom,
                                nom_complet=f"{prenom} {nom}"
                            ))
                        break

        return coureurs


def main():
    """Test du parser"""
    parser = CartonParser()

    print("🔍 Parsing des cartons UFOLEP")
    print("=" * 70)

    # Carton CX
    carton_cx = "old/data/cartons/carte CC WAMBRECHIES.pdf"
    if Path(carton_cx).exists():
        print(f"\n📄 {carton_cx}")
        coureurs_cx = parser.parse_carton_ufolep(carton_cx)
        print(f"   ✅ {len(coureurs_cx)} coureurs CX trouvés")
        for coureur in sorted(coureurs_cx, key=lambda c: c.nom_complet):
            print(f"      - {coureur.nom_complet}")

    # Carton VTT
    carton_vtt = "old/data/cartons/cartes VTT WAMBRECHIES.pdf"
    if Path(carton_vtt).exists():
        print(f"\n📄 {carton_vtt}")
        coureurs_vtt = parser.parse_carton_ufolep(carton_vtt)
        print(f"   ✅ {len(coureurs_vtt)} coureurs VTT trouvés")
        for coureur in sorted(coureurs_vtt, key=lambda c: c.nom_complet):
            print(f"      - {coureur.nom_complet}")

    # Licences FFC
    licences_ffc = "old/data/cartons/Licences_ffc.pdf"
    if Path(licences_ffc).exists():
        print(f"\n📄 {licences_ffc}")
        coureurs_ffc = parser.parse_licences_ffc(licences_ffc)
        print(f"   ✅ {len(coureurs_ffc)} coureurs FFC trouvés")
        for coureur in sorted(coureurs_ffc, key=lambda c: c.nom_complet)[:10]:
            print(f"      - {coureur.nom_complet}")


if __name__ == "__main__":
    main()
