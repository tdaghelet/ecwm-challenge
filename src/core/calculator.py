"""
Calculateur de points pour le challenge ECWM

Implémente la formule :
Points = (participation + performance × percentile) × coefficient × bonus_objectif
"""
from typing import Optional
from ..parsers.ufolep import CoureurResultat
from .config import Config
from .models import CoureurPoints, CourseMetadata


class PointsCalculator:
    """Calculateur de points basé sur le système percentile"""

    def __init__(self, config: Config):
        """
        Initialise le calculateur

        Args:
            config: Configuration du système
        """
        self.config = config

    def calculate_percentile(self, position: str, nb_participants: int) -> float:
        """
        Calcule le percentile d'un coureur

        Args:
            position: Position du coureur ("1", "2", ... ou "Ab")
            nb_participants: Nombre total de participants

        Returns:
            Percentile entre 0.0 et 1.0 (0% = dernier, 100% = premier)
        """
        if position == "Ab" or position == "Np":
            return 0.0

        try:
            pos = int(position)
        except ValueError:
            return 0.0

        if nb_participants == 0:
            return 0.0

        # Formule : (nb_total - position + 1) / nb_total
        percentile = (nb_participants - pos + 1) / nb_participants
        return max(0.0, min(1.0, percentile))  # Clamp entre 0 et 1

    def calculate_course_points(
        self,
        coureur: str,
        course_name: str,
        resultat: CoureurResultat,
        discipline: str = None,
        course_metadata: Optional[CourseMetadata] = None
    ) -> CoureurPoints:
        """
        Calcule les points pour une course

        Args:
            coureur: Nom du coureur
            course_name: Nom de la course
            resultat: Résultat du coureur (position, nb participants, etc.)
            discipline: Discipline de la course ("cx", "vtt", "route")
            course_metadata: Métadonnées de la course (optionnel, cherché auto)

        Returns:
            CoureurPoints avec le détail du calcul
        """
        # Récupérer les métadonnées si non fournies
        if course_metadata is None:
            course_metadata = self.config.get_course_metadata(course_name, discipline)
            if course_metadata is None:
                # Valeurs par défaut si la course n'est pas dans les métadonnées
                course_metadata = CourseMetadata(
                    nom=course_name,
                    discipline=discipline or "cx",
                    federation="ufolep",
                    is_objectif=False,
                    saison="unknown",
                    date_course=None
                )

        # Calculer le percentile
        percentile = self.calculate_percentile(
            resultat.position,
            resultat.nb_participants_categorie
        )

        # Récupérer les paramètres
        pts_participation = self.config.points_params.get('points_participation', 25)
        pts_perf_max = self.config.points_params.get('points_performance_max', 25)

        # Calculer les points de performance de base
        pts_performance_base = pts_perf_max * percentile
        pts_performance = pts_performance_base
        
        # Appliquer un coefficient réducteur sur les points de performance pour les petites courses
        coefficient_perf = self.config.get_coefficient_reduction(resultat.nb_participants_categorie)
        pts_performance = pts_performance_base * coefficient_perf

        # Coefficient selon type de course
        coefficient = self.config.get_coefficient(
            course_metadata.discipline,
            course_metadata.federation
        )

        # Bonus objectif (appliqué UNIQUEMENT sur la participation)
        bonus_objectif = 1.0
        if course_metadata.is_objectif:
            bonus_objectif = self.config.points_params.get('bonus_objectif', 1.5)

        # Appliquer le bonus objectif sur la participation uniquement
        pts_participation_finale = pts_participation * bonus_objectif

        # Calcul final : (participation avec bonus + performance) × coefficient
        pts_total = (pts_participation_finale + pts_performance) * coefficient

        # Arrondir au plus proche pour avoir des entiers
        pts_total = round(pts_total)

        # Si abandon, points = 0
        if resultat.position == "Ab" or resultat.position == "Np":
            pts_total = 0
            percentile = 0.0
            pts_participation_finale = 0
            pts_performance_base = 0
            pts_performance = 0

        return CoureurPoints(
            coureur=coureur,
            course=course_name,
            position=resultat.position,
            nb_participants=resultat.nb_participants_categorie,
            categorie=resultat.categorie,
            discipline=course_metadata.discipline,
            federation=course_metadata.federation,
            percentile=percentile,
            points_participation=pts_participation_finale if resultat.position not in ["Ab", "Np"] else 0,
            points_performance=pts_performance,
            coefficient=coefficient,
            bonus_objectif=bonus_objectif,
            points_total=pts_total,
            percentile_reel=pts_performance_base,  # On stocke les points de performance de base dans percentile_reel
            date_course=course_metadata.date_course
        )

    def calculate_course_points_manual(
        self,
        coureur: str,
        course_name: str,
        position: str,
        nb_participants: Optional[int],
        categorie: str = "Manual",
        discipline: str = None,
        course_metadata: Optional[CourseMetadata] = None
    ) -> CoureurPoints:
        """
        Calcule les points pour une saisie manuelle avec système hybride :
        - Si nb_participants fourni → calcul percentile normal
        - Si nb_participants = None → barème simplifié

        Args:
            coureur: Nom du coureur
            course_name: Nom de la course
            position: Position ("1", "2", ... ou "Ab")
            nb_participants: Nombre de participants (None si non fourni)
            categorie: Catégorie (optionnel)
            discipline: Discipline de la course ("cx", "vtt", "route")
            course_metadata: Métadonnées de la course (optionnel)

        Returns:
            CoureurPoints avec le détail du calcul
        """
        # Récupérer les métadonnées si non fournies
        if course_metadata is None:
            course_metadata = self.config.get_course_metadata(course_name, discipline)
            if course_metadata is None:
                # Valeurs par défaut si la course n'est pas dans les métadonnées
                course_metadata = CourseMetadata(
                    nom=course_name,
                    discipline=discipline or "cx",
                    federation="ufolep",
                    is_objectif=False,
                    saison="unknown",
                    date_course=None
                )

        # Récupérer les paramètres
        pts_participation = self.config.points_params.get('points_participation', 25)
        pts_perf_max = self.config.points_params.get('points_performance_max', 25)

        # Coefficient selon type de course
        coefficient = self.config.get_coefficient(
            course_metadata.discipline,
            course_metadata.federation
        )

        # Bonus objectif (appliqué UNIQUEMENT sur la participation)
        bonus_objectif = 1.0
        if course_metadata.is_objectif:
            bonus_objectif = self.config.points_params.get('bonus_objectif', 1.5)

        # Calculer les points de performance selon le mode
        if nb_participants is not None and nb_participants > 0:
            # MODE PERCENTILE : calcul normal avec réduction selon nb_participants
            percentile = self.calculate_percentile(position, nb_participants)
            pts_performance_base = pts_perf_max * percentile
            coefficient_perf = self.config.get_coefficient_reduction(nb_participants)
            pts_performance = pts_performance_base * coefficient_perf
        else:
            # MODE BARÈME SIMPLIFIÉ : pas de percentile, juste les points du barème
            pts_performance = self.config.get_points_bareme_simplifie(position)
            pts_performance_base = pts_performance
            percentile = 0.0  # Pas de percentile en mode simplifié

        # Appliquer le bonus objectif sur la participation uniquement
        pts_participation_finale = pts_participation * bonus_objectif

        # Calcul final : (participation avec bonus + performance) × coefficient
        pts_total = (pts_participation_finale + pts_performance) * coefficient

        # Arrondir au plus proche pour avoir des entiers
        pts_total = round(pts_total)

        # Si abandon, points = 0
        if position == "Ab" or position == "Np":
            pts_total = 0
            percentile = 0.0
            pts_participation_finale = 0
            pts_performance_base = 0
            pts_performance = 0

        return CoureurPoints(
            coureur=coureur,
            course=course_name,
            position=position,
            nb_participants=nb_participants if nb_participants is not None else 0,
            categorie=categorie,
            discipline=course_metadata.discipline,
            federation=course_metadata.federation,
            percentile=percentile,
            points_participation=pts_participation_finale if position not in ["Ab", "Np"] else 0,
            points_performance=pts_performance,
            coefficient=coefficient,
            bonus_objectif=bonus_objectif,
            points_total=pts_total,
            percentile_reel=pts_performance_base,
            date_course=course_metadata.date_course
        )
