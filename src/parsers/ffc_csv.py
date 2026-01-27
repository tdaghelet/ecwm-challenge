"""
Parser pour les fichiers CSV FFC générés par extract_ffc.py

Lit les CSV générés par l'extracteur FFC et les convertit en objets CoureurResultat
compatibles avec le reste du pipeline.
"""
import pandas as pd
from typing import List, Optional
from pathlib import Path

from src.core import utils


class FFCResultat:
    """Résultat d'un coureur dans un CSV FFC"""
    def __init__(self, coureur: str, position: str, nb_participants: int, categorie: str):
        self.coureur = coureur
        self.position = position
        self.nb_participants_categorie = nb_participants
        self.categorie = categorie


class FFCCSVParser:
    """Parser pour les CSV FFC"""
    
    @staticmethod
    def parse_course_csv(csv_path: str) -> List[FFCResultat]:
        """
        Parse un CSV FFC
        
        Args:
            csv_path: Chemin vers le CSV FFC
            
        Returns:
            Liste des résultats
        """
        try:
            # Lire le CSV (ignorer les commentaires)
            df = pd.read_csv(csv_path, comment='#')
            
            # Vérifier les colonnes
            required_cols = ['coureur', 'position', 'nb_participants', 'categorie']
            missing = [col for col in required_cols if col not in df.columns]
            
            if missing:
                print(f"⚠️  Colonnes manquantes dans {csv_path}: {missing}")
                return []
            
            # Convertir en objets FFCResultat
            resultats = []
            for _, row in df.iterrows():
                resultat = FFCResultat(
                    coureur=str(row['coureur']).strip(),
                    position=str(row['position']).strip(),
                    nb_participants=int(row['nb_participants']),
                    categorie=str(row['categorie']).strip()
                )
                resultats.append(resultat)
            
            return resultats
            
        except Exception as e:
            print(f"❌ Erreur lors du parsing de {csv_path}: {e}")
            return []
    
    @staticmethod
    def find_coureur_in_results(nom_normalise: str, resultats: List[FFCResultat]) -> Optional[FFCResultat]:
        """
        Cherche un coureur dans les résultats
        
        Args:
            nom_normalise: Nom du coureur normalisé
            resultats: Liste des résultats FFC
            
        Returns:
            FFCResultat si trouvé, None sinon
        """
        for resultat in resultats:
            # Normaliser le nom du coureur dans le résultat
            coureur_norm = utils.normalize_name(resultat.coureur)
            
            if coureur_norm == nom_normalise:
                return resultat
        
        return None
