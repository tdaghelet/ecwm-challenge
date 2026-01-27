"""
Parser pour les PDFs de résultats UFOLEP

Extrait les résultats de courses depuis les PDFs UFOLEP en gérant :
- Les différentes catégories dans un même PDF
- Les positions et abandons
- Le nombre de participants par catégorie
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pdfplumber
import re

from src.core import utils


@dataclass
class CoureurResultat:
    """Résultat d'un coureur dans une course"""
    nom: str  # Nom normalisé (PRENOM NOM)
    position: str  # "1", "2", ... ou "Ab"
    categorie: str  # "1ère Catégorie", "2ème Catégorie", etc.
    nb_participants_categorie: int  # Nombre total dans cette catégorie


@dataclass
class CategorieResultats:
    """Résultats d'une catégorie"""
    nom: str  # "1ère Catégorie", "Féminines", etc.
    positions: Dict[str, str]  # {nom_normalisé: position}
    nb_participants: int  # Nombre total de coureurs (hors Ab)
    nb_abandons: int  # Nombre d'abandons


class UfolepPDFParser:
    """Parser pour les fichiers PDF UFOLEP"""

    # Mots-clés qui indiquent la fin du classement
    STOP_KEYWORDS = ["ETAT TOUR PAR TOUR", "Meilleur tour", "Tps. tour"]

    # Patterns pour détecter les titres de catégories
    CATEGORY_PATTERNS = [
        r"^1[èe]re?\s+Cat[ée]gorie",
        r"^2[èe]me\s+Cat[ée]gorie",
        r"^3[èe]me\s+Cat[ée]gorie",
        r"^4[èe]me\s+Cat[ée]gorie",
        r"^F[ée]minines?",
        r"^Cadets?",
        r"^Minimes?",
        r"^Benjamins?",
        r"^Pupilles?",
        r"^Poussins?",
        # Patterns pour les courses CX avec nomenclature VTT
        r"^VTT\s+Juniors?",
        r"^VTT\s+S[ée]niors?\s+[ABC]",
        r"^VTT\s+V[ée]t[ée]rans?\s+[ABC]",
        r"^VTT\s+Cadets?",
        r"^VTT\s+Minimes?",
        r"^VTT\s+Benjamins?",
        r"^VTT\s+Pupilles?",
        r"^VTT\s+Poussins?",
        r"^VTT\s+F[ée]minines?",
    ]

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extrait le texte du PDF jusqu'aux sections "tour par tour"

        Args:
            pdf_path: Chemin vers le PDF

        Returns:
            Texte complet du classement
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Arrêter si on trouve les mots-clés de fin
                        if any(keyword in page_text for keyword in self.STOP_KEYWORDS):
                            break
                        text += page_text + "\n"
            return text
        except Exception as e:
            print(f"Erreur lors de l'extraction du PDF {pdf_path}: {e}")
            return ""

    def is_category_header(self, line: str) -> bool:
        """Vérifie si une ligne est un titre de catégorie"""
        line = line.strip()
        for pattern in self.CATEGORY_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False

    def parse_categories(self, text: str) -> List[CategorieResultats]:
        """
        Parse le texte pour extraire les catégories et leurs résultats

        Args:
            text: Texte complet extrait du PDF

        Returns:
            Liste des catégories avec leurs résultats
        """
        categories = []
        lines = text.split('\n')

        current_category = None
        current_positions = {}
        current_abandons = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Nouvelle catégorie détectée
            if self.is_category_header(line):
                # Sauvegarder la catégorie précédente si elle existe
                if current_category:
                    categories.append(CategorieResultats(
                        nom=current_category,
                        positions=current_positions,
                        nb_participants=len(current_positions),
                        nb_abandons=len(current_abandons)
                    ))

                # Initialiser la nouvelle catégorie
                current_category = line
                current_positions = {}
                current_abandons = []
                continue

            # Extraire position et nom
            # Format: "1 LEFEVRE EDDY UNION VELOCIPEDIQUE..."
            # ou "Ab DUFRENOIS MAXENCE ..."
            match = re.match(r'^(Ab|\d+)\s+(.+)$', line)
            if match and current_category:
                position = match.group(1)
                rest = match.group(2)

                # Extraire le nom (2 premiers mots en majuscules = PRENOM NOM)
                words = rest.split()
                name_words = []
                for word in words:
                    # Vérifier si c'est un mot de nom (majuscules, accents, tirets)
                    if re.match(r"^[A-ZÉÈÀÂÎÔÙÇ\-']+$", word):
                        name_words.append(word)
                    else:
                        break
                    if len(name_words) >= 2:  # Max 2 mots (PRENOM NOM)
                        break

                if name_words:
                    nom = utils.normalize_name(' '.join(name_words))
                    if position == "Ab":
                        current_abandons.append(nom)
                    else:
                        current_positions[nom] = position

        # Sauvegarder la dernière catégorie
        if current_category:
            categories.append(CategorieResultats(
                nom=current_category,
                positions=current_positions,
                nb_participants=len(current_positions),
                nb_abandons=len(current_abandons)
            ))

        return categories

    def find_coureur_in_categories(
        self,
        nom_coureur: str,
        categories: List[CategorieResultats]
    ) -> Optional[CoureurResultat]:
        """
        Recherche un coureur dans les catégories

        Utilise un matching exact puis fuzzy si nécessaire

        Args:
            nom_coureur: Nom du coureur à chercher (déjà normalisé)
            categories: Liste des catégories de la course

        Returns:
            CoureurResultat si trouvé, None sinon
        """
        # Recherche exacte
        for cat in categories:
            if nom_coureur in cat.positions:
                return CoureurResultat(
                    nom=nom_coureur,
                    position=cat.positions[nom_coureur],
                    categorie=cat.nom,
                    nb_participants_categorie=cat.nb_participants
                )

        # Recherche fuzzy (par préfixe)
        nb_mots = len(nom_coureur.split())
        coureur_words = nom_coureur.split()

        for cat in categories:
            for key in cat.positions:
                key_words = key.split()
                # Match sur les N premiers mots
                if key_words[:nb_mots] == coureur_words:
                    return CoureurResultat(
                        nom=nom_coureur,
                        position=cat.positions[key],
                        categorie=cat.nom,
                        nb_participants_categorie=cat.nb_participants
                    )

        # Recherche fuzzy alternative (sans espaces)
        coureur_alt = utils.normalize_name_strict(nom_coureur)
        for cat in categories:
            for key in cat.positions:
                key_words = key.split()
                if utils.normalize_name_strict(" ".join(key_words[:nb_mots])) == coureur_alt:
                    return CoureurResultat(
                        nom=nom_coureur,
                        position=cat.positions[key],
                        categorie=cat.nom,
                        nb_participants_categorie=cat.nb_participants
                    )

        return None

    def parse_course(self, pdf_path: str) -> List[CategorieResultats]:
        """
        Parse un PDF complet de course UFOLEP

        Args:
            pdf_path: Chemin vers le PDF

        Returns:
            Liste des catégories avec résultats
        """
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            return []

        categories = self.parse_categories(text)
        return categories
