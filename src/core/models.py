"""
Modèles de données pour le système de challenge
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CourseMetadata:
    """Métadonnées d'une course"""
    nom: str
    discipline: str  # "cx" ou "route"
    federation: str  # "ufolep" ou "ffc"
    is_objectif: bool
    saison: str
    date_course: Optional[str] = None  # Format YYYY-MM-DD

    @property
    def type_course(self) -> str:
        """Retourne le type de course pour les coefficients (ex: cx_ufolep)"""
        return f"{self.discipline}_{self.federation}"


@dataclass
class CoureurPoints:
    """Points d'un coureur pour une course"""
    coureur: str
    course: str
    position: str  # "1", "2", ... ou "Ab"
    nb_participants: int
    categorie: str
    discipline: str  # "cx", "vtt", "route"
    federation: str  # "ufolep", "ffc", etc.
    percentile: float  # Percentile appliqué (après plafonnement éventuel)
    points_participation: float
    points_performance: float
    coefficient: float
    bonus_objectif: float
    points_total: int  # Entier arrondi
    percentile_reel: float = None  # Percentile réel avant plafonnement (optionnel)
    date_course: Optional[str] = None  # Format YYYY-MM-DD

    def __str__(self) -> str:
        if self.position == "Ab":
            return f"{self.course}: Ab (0 pts)"
        return (f"{self.course}: {self.position}e/{self.nb_participants} "
                f"({self.percentile:.1%}) = {self.points_total} pts")


@dataclass
class CoureurClassement:
    """Classement général d'un coureur"""
    nom: str
    courses_detail: List[CoureurPoints] = field(default_factory=list)
    nb_courses: int = 0
    nb_courses_objectif: int = 0
    points_courses: int = 0  # Entier
    bonus_badges: int = 0  # Bonus des badges (gamification)
    points_total: int = 0  # Entier

    def add_course(self, course_points: CoureurPoints) -> None:
        """Ajoute les points d'une course"""
        self.courses_detail.append(course_points)
        self.nb_courses += 1
        self.points_courses += course_points.points_total

    def update_totals(self, bonus_badges: int = 0) -> None:
        """Met à jour les totaux avec les bonus des badges"""
        self.bonus_badges = bonus_badges
        self.points_total = self.points_courses + bonus_badges

    def get_courses_by_type(self, type_course: str) -> List[CoureurPoints]:
        """Retourne les courses d'un type donné"""
        # Pour l'instant on n'a pas le type dans CoureurPoints
        # On pourra l'ajouter plus tard si nécessaire
        return self.courses_detail
