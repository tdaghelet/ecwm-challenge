"""
Parser pour les saisies manuelles (CSV ou Google Sheets)

Permet d'intégrer des résultats saisis manuellement dans le challenge.
Format : CSV avec colonnes course_name, coureur, position, nb_participants, etc.
"""
import os
import ssl
import pandas as pd
from typing import List, Optional
from dataclasses import dataclass

from src.core import utils


@dataclass
class ManualResult:
    """Résultat saisi manuellement"""
    course_name: str
    coureur: str
    position: str  # "1", "2", ... ou "Ab"
    nb_participants: Optional[int]  # None si non fourni
    categorie: Optional[str]
    discipline: str
    federation: str
    date: Optional[str]


class ManualParser:
    """Parser pour les saisies manuelles"""

    def parse_source(self, source_url: str) -> List[ManualResult]:
        """
        Parse une source (URL Google Sheet ou fichier CSV local)

        Args:
            source_url: URL du CSV publié ou chemin du fichier local

        Returns:
            Liste des résultats manuels
        """
        try:
            # Créer un contexte SSL qui ignore la vérification (pour macOS)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # Lire le CSV (fonctionne pour URL et fichier local)
            if source_url.startswith('http'):
                # Pour les URLs, utiliser le contexte SSL
                import urllib.request
                storage_options = {'client_kwargs': {'verify': False}}
                # Utiliser urllib directement pour éviter les problèmes SSL
                with urllib.request.urlopen(source_url, context=ssl_context) as response:
                    df = pd.read_csv(response, comment='#')
            else:
                # Pour les fichiers locaux
                df = pd.read_csv(source_url, comment='#')

            # Vérifier les colonnes obligatoires
            required_cols = ['course_name', 'coureur', 'position', 'discipline', 'federation']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                print(f"⚠️  Colonnes manquantes dans {source_url}: {missing_cols}")
                return []

            results = []
            for _, row in df.iterrows():
                # Parser nb_participants (peut être vide)
                nb_participants = None
                if 'nb_participants' in row and pd.notna(row['nb_participants']):
                    try:
                        nb_participants = int(row['nb_participants'])
                    except (ValueError, TypeError):
                        pass

                # Parser categorie (optionnel)
                categorie = None
                if 'categorie' in row and pd.notna(row['categorie']):
                    categorie = str(row['categorie'])

                # Parser date (optionnel)
                date = None
                if 'date' in row and pd.notna(row['date']):
                    date = str(row['date'])

                result = ManualResult(
                    course_name=str(row['course_name']).strip().lower(),
                    coureur=utils.normalize_name(str(row['coureur'])),
                    position=str(row['position']).strip(),
                    nb_participants=nb_participants,
                    categorie=categorie,
                    discipline=str(row['discipline']).strip().lower(),
                    federation=str(row['federation']).strip().lower(),
                    date=date
                )
                results.append(result)

            return results

        except Exception as e:
            print(f"❌ Erreur lors du parsing de {source_url}: {e}")
            return []

    def load_all_sources(self, config_path: str = "data/sources_config.csv") -> List[ManualResult]:
        """
        Charge tous les résultats depuis toutes les sources actives

        Args:
            config_path: Chemin vers le fichier de config des sources

        Returns:
            Liste de tous les résultats manuels
        """
        if not os.path.exists(config_path):
            print(f"ℹ️  Pas de fichier {config_path}, saisie manuelle désactivée")
            return []

        try:
            # Lire la config (ignorer les commentaires)
            df_config = pd.read_csv(config_path, comment='#')

            all_results = []
            active_sources = df_config[df_config['actif'] == 1]

            if len(active_sources) == 0:
                print("ℹ️  Aucune source manuelle active")
                return []

            print(f"\n📝 Chargement des saisies manuelles")
            print("-" * 70)

            for _, source in active_sources.iterrows():
                source_url = source['url']
                description = source.get('description', source_url)

                print(f"   📄 {description}...", end=" ")

                results = self.parse_source(source_url)

                if results:
                    all_results.extend(results)
                    print(f"✅ {len(results)} résultats")
                else:
                    print("⚠️  Aucun résultat")

            print()
            return all_results

        except Exception as e:
            print(f"❌ Erreur lors du chargement des sources: {e}")
            return []
