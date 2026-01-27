"""
Gestion de la configuration du système
Charge tous les paramètres depuis les fichiers CSV
"""
import os
import pandas as pd
from typing import Dict, List, Tuple
from .models import CourseMetadata


class Config:
    """Gestionnaire de configuration centralisé"""

    def __init__(self, data_dir: str = "data"):
        """
        Initialise la configuration

        Args:
            data_dir: Répertoire contenant les fichiers de config
        """
        self.data_dir = data_dir
        self.points_params: Dict[str, float] = {}
        self.courses_metadata: Dict[str, CourseMetadata] = {}
        self.coureurs: List[str] = []
        self.paliers_reduction: List[Tuple[int, int, float]] = []  # (min, max, coefficient)
        self.bareme_simplifie: List[Tuple[int, int, int]] = []  # (position_min, position_max, points)

        # Charger toutes les configs
        self.load_all()

    def load_all(self) -> None:
        """Charge toutes les configurations"""
        self.load_points_config()
        self.load_paliers_reduction()
        self.load_bareme_simplifie()
        self.load_courses_metadata()
        self.load_coureurs()

    def load_points_config(self) -> None:
        """Charge les paramètres de points depuis config_points.csv"""
        path = os.path.join(self.data_dir, "config_points.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Fichier de config introuvable: {path}")

        df = pd.read_csv(path)
        for _, row in df.iterrows():
            param = row['parametre']
            valeur = float(row['valeur'])
            self.points_params[param] = valeur

    def load_paliers_reduction(self) -> None:
        """Charge les paliers de réduction des points de performance"""
        path = os.path.join(self.data_dir, "paliers_reduction.csv")
        if not os.path.exists(path):
            print(f"⚠️  Fichier {path} non trouvé, pas de réduction sur petites courses")
            return

        df = pd.read_csv(path)
        self.paliers_reduction = []
        for _, row in df.iterrows():
            nb_min = int(row['nb_participants_min'])
            nb_max = int(row['nb_participants_max'])
            coef = float(row['coefficient_reduction'])
            self.paliers_reduction.append((nb_min, nb_max, coef))

        # Trier par nb_min
        self.paliers_reduction.sort()
        print(f"   ✅ {len(self.paliers_reduction)} paliers de réduction chargés")

    def get_coefficient_reduction(self, nb_participants: int) -> float:
        """
        Retourne le coefficient de réduction selon le nombre de participants

        Args:
            nb_participants: Nombre de participants dans la course

        Returns:
            Coefficient à appliquer (0.5 = 50%, 1.0 = 100%)
        """
        for nb_min, nb_max, coef in self.paliers_reduction:
            if nb_min <= nb_participants <= nb_max:
                return coef
        return 1.0  # Par défaut, pas de réduction

    def load_bareme_simplifie(self) -> None:
        """Charge le barème simplifié pour saisie manuelle sans nb_participants"""
        path = os.path.join(self.data_dir, "bareme_simplifie.csv")
        if not os.path.exists(path):
            print(f"⚠️  Fichier {path} non trouvé, pas de barème simplifié disponible")
            return

        df = pd.read_csv(path)
        self.bareme_simplifie = []
        for _, row in df.iterrows():
            pos_min = int(row['position_min'])
            pos_max = int(row['position_max'])
            points = int(row['points_performance'])
            self.bareme_simplifie.append((pos_min, pos_max, points))

        # Trier par position_min
        self.bareme_simplifie.sort()
        print(f"   ✅ {len(self.bareme_simplifie)} paliers de barème simplifié chargés")

    def get_points_bareme_simplifie(self, position: str) -> float:
        """
        Retourne les points de performance selon le barème simplifié

        Args:
            position: Position du coureur ("1", "2", ... ou "Ab")

        Returns:
            Points de performance (0 si abandon ou position non trouvée)
        """
        if position == "Ab" or position == "Np":
            return 0.0

        try:
            pos = int(position)
        except ValueError:
            return 0.0

        for pos_min, pos_max, points in self.bareme_simplifie:
            if pos_min <= pos <= pos_max:
                return float(points)

        return 0.0  # Par défaut, 0 points si hors barème

    def load_courses_metadata(self) -> None:
        """Charge les métadonnées des courses depuis courses_metadata.csv"""
        path = os.path.join(self.data_dir, "courses_metadata.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Fichier de métadonnées introuvable: {path}")

        df = pd.read_csv(path)
        self.courses_metadata = {}
        for _, row in df.iterrows():
            # Gérer les deux formats de colonne (nom_course et nom)
            nom = row.get('nom', row.get('nom_course', '')).strip().lower()
            discipline = row['discipline'].strip().lower()
            metadata = CourseMetadata(
                nom=nom,
                discipline=discipline,
                federation=row['federation'].strip().lower(),
                is_objectif=str(row['is_objectif']).lower() == 'true',
                saison=row['saison'].strip()
            )
            # Utiliser (nom, discipline) comme clé composite
            key = (nom, discipline)
            self.courses_metadata[key] = metadata

    def load_coureurs(self) -> None:
        """Charge la liste des coureurs depuis ecwm_coureurs.csv"""
        path = os.path.join(self.data_dir, "ecwm_coureurs.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Fichier de coureurs introuvable: {path}")

        df = pd.read_csv(path, dtype=str)
        self.coureurs = df['COUREUR'].tolist()
        
        # Stocker aussi les disciplines autorisées par coureur
        self.coureurs_disciplines = {}
        for _, row in df.iterrows():
            coureur = row['COUREUR']
            disciplines = []
            
            # UFOLEP
            if row.get('ufolep_cx') == '1':
                disciplines.append(('cx', 'ufolep'))
            if row.get('ufolep_route') == '1':
                disciplines.append(('route', 'ufolep'))
            if row.get('ufolep_vtt') == '1':
                disciplines.append(('vtt', 'ufolep'))
            
            # FFC
            if row.get('ffc_cx') == '1':
                disciplines.append(('cx', 'ffc'))
            if row.get('ffc_route') == '1':
                disciplines.append(('route', 'ffc'))
            
            self.coureurs_disciplines[coureur] = disciplines
    
    def coureur_autorise(self, coureur: str, discipline: str, federation: str = 'ufolep') -> bool:
        """
        Vérifie si un coureur est autorisé à participer à une discipline
        
        Args:
            coureur: Nom du coureur
            discipline: Discipline ("cx", "route", "vtt")
            federation: Fédération ("ufolep", "ffc")
        
        Returns:
            True si le coureur est autorisé
        """
        if coureur not in self.coureurs_disciplines:
            return False
        
        return (discipline, federation) in self.coureurs_disciplines[coureur]

    def get_coefficient(self, discipline: str, federation: str) -> float:
        """
        Retourne le coefficient pour un type de course

        Args:
            discipline: "cx" ou "route"
            federation: "ufolep" ou "ffc"

        Returns:
            Coefficient (1.0 par défaut si non trouvé)
        """
        param_name = f"coef_{discipline}_{federation}"
        return self.points_params.get(param_name, 1.0)

    def get_course_metadata(self, nom_course: str, discipline: str = None) -> CourseMetadata:
        """
        Retourne les métadonnées d'une course

        Args:
            nom_course: Nom de la course (normalisé)
            discipline: Discipline de la course ("cx", "route", "vtt")
                       Si None, essaie de trouver sans discipline

        Returns:
            CourseMetadata ou None si non trouvée
        """
        nom_norm = nom_course.strip().lower()
        
        if discipline:
            # Recherche avec discipline spécifique
            key = (nom_norm, discipline.lower())
            return self.courses_metadata.get(key)
        else:
            # Recherche sans discipline (pour rétrocompatibilité)
            # Essaie de trouver n'importe quelle discipline
            for key, metadata in self.courses_metadata.items():
                if key[0] == nom_norm:
                    return metadata
            return None

    def __repr__(self) -> str:
        return (f"Config(points_params={len(self.points_params)}, "
                f"courses={len(self.courses_metadata)}, "
                f"coureurs={len(self.coureurs)})")
