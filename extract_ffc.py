#!/usr/bin/env python3
"""
Extracteur de résultats FFC depuis les pages web

Parse les URLs FFC configurées dans data/ffc_sources.csv
et génère un CSV par course dans classements/ffc/{saison}/

Usage:
    python3 extract_ffc.py              # Parse uniquement les nouvelles URLs
    python3 extract_ffc.py --force-extract  # Re-parse toutes les URLs
"""
import argparse
import os
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import List
from dataclasses import dataclass
from pathlib import Path
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class FFCResult:
    """Résultat d'un coureur FFC"""
    coureur: str  # Format: "NOM PRENOM"
    position: str
    nb_participants: int
    categorie: str


class FFCExtractor:
    """Extracteur de résultats depuis les pages FFC"""
    
    def __init__(self, sources_file: str = "data/ffc_sources.csv",
                 base_output_dir: str = "classements/ffc"):
        """
        Initialise l'extracteur
        
        Args:
            sources_file: Fichier CSV contenant les URLs à parser
            base_output_dir: Répertoire de base pour les CSV de sortie
        """
        self.sources_file = sources_file
        self.base_output_dir = Path(base_output_dir)
        
    def load_sources(self) -> pd.DataFrame:
        """Charge les sources depuis le fichier CSV"""
        if not os.path.exists(self.sources_file):
            print(f"❌ Fichier {self.sources_file} introuvable")
            sys.exit(1)
            
        df = pd.read_csv(self.sources_file, comment='#')
        required_cols = ['course_name', 'date', 'discipline', 'saison', 'url']
        
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"❌ Colonnes manquantes dans {self.sources_file}: {missing}")
            sys.exit(1)
            
        return df
    
    def get_output_path(self, course_name: str, saison: str) -> Path:
        """
        Détermine le chemin du fichier CSV de sortie
        
        Args:
            course_name: Nom de la course
            saison: Saison (ex: cx-25-26)
            
        Returns:
            Path du fichier CSV
        """
        output_dir = self.base_output_dir / saison
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{course_name}.csv"
    
    def parse_ffc_page(self, url: str) -> List[FFCResult]:
        """
        Parse une page de résultats FFC
        
        Args:
            url: URL de la page FFC
            
        Returns:
            Liste des résultats extraits
        """
        try:
            # Récupérer la page
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Trouver tous les tableaux
            tables = soup.find_all('table')
            
            if not tables:
                return []
            
            results = []
            
            # Parser chaque tableau (une catégorie par tableau)
            for table in tables:
                # Trouver l'en-tête de catégorie (h2 ou h3 avant le tableau)
                categorie = "Unknown"
                prev_element = table.find_previous(['h2', 'h3', 'h4'])
                if prev_element:
                    categorie = prev_element.text.strip()
                
                # Parser les lignes du tableau
                rows = table.find_all('tr')
                
                # Ignorer la première ligne (en-têtes)
                data_rows = rows[1:]
                
                if not data_rows:
                    continue
                
                # Le nombre de participants = dernière position
                nb_participants = len(data_rows)
                
                for row in data_rows:
                    cols = row.find_all('td')
                    
                    if len(cols) < 4:  # Minimum: Rang, Nom, Prénom, ...
                        continue
                    
                    # Extraire les données
                    position = cols[0].text.strip()
                    
                    # Ignorer les lignes sans position valide
                    if not position or not position.isdigit():
                        continue
                    
                    # UCIID = cols[1] (on ne l'utilise pas pour l'instant)
                    nom = cols[2].text.strip().upper()
                    prenom = cols[3].text.strip().upper()
                    
                    # Format coureur : "NOM PRENOM"
                    coureur = f"{nom} {prenom}"
                    
                    result = FFCResult(
                        coureur=coureur,
                        position=position,
                        nb_participants=nb_participants,
                        categorie=categorie
                    )
                    results.append(result)
            
            return results
            
        except requests.RequestException as e:
            print(f"❌ Erreur HTTP: {e}")
            return []
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return []
    
    def save_course_csv(self, results: List[FFCResult], course_name: str, saison: str) -> None:
        """
        Sauvegarde les résultats d'une course dans un CSV
        
        Args:
            results: Liste des résultats
            course_name: Nom de la course
            saison: Saison (ex: cx-25-26)
        """
        if not results:
            return
        
        # Convertir en DataFrame
        data = []
        for result in results:
            data.append({
                'coureur': result.coureur,
                'position': result.position,
                'nb_participants': result.nb_participants,
                'categorie': result.categorie
            })
        
        df = pd.DataFrame(data)
        
        # Déterminer le chemin de sortie
        output_path = self.get_output_path(course_name, saison)
        
        # Sauvegarder avec en-tête commenté
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Course FFC: {course_name}\n")
            f.write(f"# Saison: {saison}\n")
            f.write(f"# Nombre total de résultats: {len(results)}\n")
        
        df.to_csv(output_path, index=False, mode='a')
    
    def run(self, force_extract: bool = False) -> None:
        """
        Exécute l'extraction
        
        Args:
            force_extract: Si True, re-parse toutes les URLs
        """
        print("🏁 Extraction des résultats FFC")
        print("=" * 70)
        print()
        
        # Charger les sources
        df_sources = self.load_sources()
        print(f"📋 {len(df_sources)} URLs configurées")
        
        # Grouper par course_name (plusieurs URLs peuvent pointer vers la même course)
        courses_grouped = df_sources.groupby('course_name')
        print(f"   {len(courses_grouped)} courses uniques")
        print()
        
        print("🔍 Extraction en cours...")
        print("-" * 70)
        
        new_count = 0
        skipped_count = 0
        error_count = 0
        
        for course_name, group in courses_grouped:
            # Prendre les infos de la première ligne du groupe
            first_row = group.iloc[0]
            saison = first_row['saison']
            discipline = first_row['discipline']
            
            # Vérifier si le fichier existe déjà
            output_path = self.get_output_path(course_name, saison)
            
            if output_path.exists() and not force_extract:
                print(f"   ⏭️  {course_name:20s} (déjà extrait)")
                skipped_count += 1
                continue
            
            # Parser toutes les URLs de cette course et agréger les résultats
            print(f"   📄 {course_name:20s} ({len(group)} URLs) ", end="")
            all_results = []
            
            for _, source in group.iterrows():
                url = source['url']
                results = self.parse_ffc_page(url)
                if results:
                    all_results.extend(results)
            
            if all_results:
                # Sauvegarder le CSV avec tous les résultats agrégés
                self.save_course_csv(all_results, course_name, saison)
                print(f"✅ {len(all_results)} résultats")
                new_count += 1
            else:
                print("⚠️  Aucun résultat")
                error_count += 1
        
        print()
        
        # Résumé
        print("📊 Résumé")
        print("-" * 70)
        print(f"   ✅ {new_count} nouvelles courses extraites")
        print(f"   ⏭️  {skipped_count} courses déjà en cache")
        if error_count > 0:
            print(f"   ⚠️  {error_count} erreurs")
        print(f"   💾 Fichiers dans: {self.base_output_dir}/")
        print()
        print("✅ Terminé !")
        print("=" * 70)


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Extracteur de résultats FFC depuis les pages web"
    )
    parser.add_argument(
        '--force-extract',
        action='store_true',
        help="Re-parse toutes les URLs (ignore le cache)"
    )
    parser.add_argument(
        '--sources',
        default='data/ffc_sources.csv',
        help="Fichier CSV des sources (défaut: data/ffc_sources.csv)"
    )
    parser.add_argument(
        '--output-dir',
        default='classements/ffc',
        help="Répertoire de base pour les CSV (défaut: classements/ffc)"
    )
    
    args = parser.parse_args()
    
    extractor = FFCExtractor(
        sources_file=args.sources,
        base_output_dir=args.output_dir
    )
    
    extractor.run(force_extract=args.force_extract)


if __name__ == "__main__":
    main()
