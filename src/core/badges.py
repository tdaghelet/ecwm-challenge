"""
Module de calcul des badges de gamification
"""
import os
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional
from src.core.models import CoureurClassement, CourseMetadata


@dataclass
class Badge:
    """Définition d'un badge"""
    badge_id: str
    nom: str
    emoji: str
    description: str
    type: str  # "palier" ou "unique"
    critere: str
    niveau: Optional[str]  # Bronze, Argent, Or, etc.
    seuil: float
    actif: bool
    bonus_points: int  # Points bonus accordés pour ce badge


@dataclass
class BadgeObtenu:
    """Badge obtenu par un coureur"""
    badge_id: str
    nom: str
    emoji: str
    description: str
    niveau: Optional[str]
    valeur_obtenue: float  # La valeur qui a permis d'obtenir le badge
    bonus_points: int  # Points bonus accordés par ce badge


class BadgeCalculator:
    """Calculateur de badges pour les coureurs"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialise le calculateur

        Args:
            config_dir: Répertoire contenant badges.csv
        """
        self.badges: List[Badge] = []
        self.load_badges_config(config_dir)

    def load_badges_config(self, config_dir: str) -> None:
        """
        Charge la configuration des badges depuis le CSV

        Args:
            config_dir: Répertoire contenant le fichier de config
        """
        csv_path = os.path.join(config_dir, "badges.csv")

        if not os.path.exists(csv_path):
            print(f"⚠️  Fichier {csv_path} non trouvé, badges désactivés")
            return

        df = pd.read_csv(csv_path)

        for _, row in df.iterrows():
            if row['actif'] == 1:
                badge = Badge(
                    badge_id=row['badge_id'],
                    nom=row['nom'],
                    emoji=row['emoji'],
                    description=row['description'],
                    type=row['type'],
                    critere=row['critere'],
                    niveau=row['niveau'] if pd.notna(row['niveau']) and row['niveau'] else None,
                    seuil=float(row['seuil']),
                    actif=bool(row['actif']),
                    bonus_points=int(row['bonus_points']) if 'bonus_points' in row and pd.notna(row['bonus_points']) else 0
                )
                self.badges.append(badge)

        print(f"   ✅ {len(self.badges)} badges chargés")

    def calculate_badges(
        self,
        coureur: CoureurClassement,
        courses_metadata: Dict[str, CourseMetadata],
        total_courses_saison: int
    ) -> List[BadgeObtenu]:
        """
        Calcule les badges obtenus par un coureur

        Args:
            coureur: Classement du coureur
            courses_metadata: Métadonnées des courses
            total_courses_saison: Nombre total de courses dans la saison

        Returns:
            Liste des badges obtenus
        """
        badges_obtenus = []

        # Calculer les statistiques du coureur
        stats = self._calculate_stats(coureur, courses_metadata, total_courses_saison)

        # Grouper les badges à paliers
        badges_paliers = {}
        for badge in self.badges:
            if badge.type == "palier":
                if badge.nom not in badges_paliers:
                    badges_paliers[badge.nom] = []
                badges_paliers[badge.nom].append(badge)
            else:
                # Badge unique
                if self._check_critere(badge, stats):
                    badges_obtenus.append(BadgeObtenu(
                        badge_id=badge.badge_id,
                        nom=badge.nom,
                        emoji=badge.emoji,
                        description=badge.description,
                        niveau=badge.niveau,
                        valeur_obtenue=stats.get(badge.critere, 0),
                        bonus_points=badge.bonus_points
                    ))

        # Pour les badges à paliers, ne garder que le plus haut niveau atteint
        for nom_badge, badges_list in badges_paliers.items():
            # Trier par seuil décroissant
            badges_list.sort(key=lambda b: b.seuil, reverse=True)

            # Trouver le plus haut niveau atteint
            for badge in badges_list:
                if self._check_critere(badge, stats):
                    badges_obtenus.append(BadgeObtenu(
                        badge_id=badge.badge_id,
                        nom=badge.nom,
                        emoji=badge.emoji,
                        description=badge.description,
                        niveau=badge.niveau,
                        valeur_obtenue=stats.get(badge.critere, 0),
                        bonus_points=badge.bonus_points
                    ))
                    break  # On ne garde que le plus haut niveau

        return badges_obtenus

    def _calculate_stats(
        self,
        coureur: CoureurClassement,
        courses_metadata: Dict[str, CourseMetadata],
        total_courses_saison: int
    ) -> Dict[str, float]:
        """
        Calcule les statistiques nécessaires pour les badges

        Args:
            coureur: Classement du coureur
            courses_metadata: Métadonnées des courses
            total_courses_saison: Nombre total de courses dans la saison

        Returns:
            Dictionnaire des statistiques
        """
        nb_podiums = 0
        nb_top10 = 0
        nb_abandons = 0
        nb_courses_objectif = 0
        federations = set()
        disciplines = set()
        percentiles = []

        # Parcourir les courses du coureur
        for course_points in coureur.courses_detail:
            # Podiums et top 10
            if course_points.position != "Ab":
                try:
                    position = int(course_points.position)
                    if position <= 3:
                        nb_podiums += 1
                    if position <= 10:
                        nb_top10 += 1
                    percentiles.append(course_points.percentile)
                except ValueError:
                    pass
            else:
                nb_abandons += 1

            # Courses objectif - utiliser la discipline stockée dans course_points
            metadata = courses_metadata.get((course_points.course, course_points.discipline))
            if metadata and metadata.is_objectif:
                nb_courses_objectif += 1

            # Fédérations et disciplines - utiliser directement course_points
            disciplines.add(course_points.discipline)
            
            # Pour la fédération, on peut aussi l'utiliser si disponible dans metadata
            if metadata:
                federations.add(metadata.federation)

        # Calculs des moyennes et pourcentages
        percentile_moyen = (sum(percentiles) / len(percentiles) * 100) if percentiles else 0
        taux_participation = (coureur.nb_courses / total_courses_saison * 100) if total_courses_saison > 0 else 0

        # Multi-discipline : Route ET (CX OU VTT)
        has_route = 'route' in disciplines
        has_cx_or_vtt = 'cx' in disciplines or 'vtt' in disciplines
        multi_discipline = 100 if (has_route and has_cx_or_vtt) else 0

        return {
            'nb_courses': coureur.nb_courses,
            'nb_podiums': nb_podiums,
            'nb_top10': nb_top10,
            'nb_courses_objectif': nb_courses_objectif,
            'nb_abandons': nb_abandons,
            'deux_federations': 100 if len(federations) >= 2 else 0,
            'deux_disciplines': multi_discipline,
            'percentile_moyen': percentile_moyen,
            'taux_participation': taux_participation
        }

    def _check_critere(self, badge: Badge, stats: Dict[str, float]) -> bool:
        """
        Vérifie si le critère d'un badge est rempli

        Args:
            badge: Badge à vérifier
            stats: Statistiques du coureur

        Returns:
            True si le critère est rempli
        """
        valeur = stats.get(badge.critere, 0)

        # Règle spéciale pour le badge Performeur : nécessite au moins 5 courses
        if badge.badge_id == 'performeur':
            nb_courses = stats.get('nb_courses', 0)
            return valeur >= badge.seuil and nb_courses >= 5

        return valeur >= badge.seuil
