#!/usr/bin/env python3
"""
Génère automatiquement le fichier courses_metadata.csv
en scannant les PDFs disponibles dans classements/
"""
import os
import csv
from pathlib import Path

from src.core import utils


def scan_courses(base_dir: str = "classements") -> dict:
    """
    Scanne les répertoires de courses et retourne la liste complète
    
    Args:
        base_dir: Répertoire de base contenant les courses
        
    Returns:
        Dict {(nom, discipline): federation}
    """
    courses = {}
    
    # Scanner UFOLEP
    ufolep_cx_dir = os.path.join(base_dir, "ufolep", "cx-25-26")
    ufolep_vtt_dir = os.path.join(base_dir, "ufolep", "vtt-25-26")
    
    if os.path.exists(ufolep_cx_dir):
        for filename in os.listdir(ufolep_cx_dir):
            if filename.endswith('.pdf'):
                course_name = utils.extract_course_name(filename)
                courses[(course_name, 'cx')] = 'ufolep'

    if os.path.exists(ufolep_vtt_dir):
        for filename in os.listdir(ufolep_vtt_dir):
            if filename.endswith('.pdf'):
                course_name = utils.extract_course_name(filename)
                courses[(course_name, 'vtt')] = 'ufolep'
    
    # Scanner FFC (si disponible)
    ffc_dir = os.path.join(base_dir, "ffc")
    if os.path.exists(ffc_dir):
        for subdir in os.listdir(ffc_dir):
            subdir_path = os.path.join(ffc_dir, subdir)
            if os.path.isdir(subdir_path):
                # Détecter la discipline depuis le nom du dossier
                discipline = 'cx' if 'cx' in subdir.lower() else 'route'
                
                for filename in os.listdir(subdir_path):
                    if filename.endswith('.csv'):  # CSV pour FFC, pas PDF
                        course_name = utils.extract_course_name(filename)
                        courses[(course_name, discipline)] = 'ffc'
    
    return courses


def load_existing_metadata(csv_path: str) -> dict:
    """
    Charge les métadonnées existantes (courses objectif, etc.)
    
    Args:
        csv_path: Chemin vers courses_metadata.csv
        
    Returns:
        Dict {(nom, discipline): {is_objectif, saison}}
    """
    metadata = {}
    
    if not os.path.exists(csv_path):
        return metadata
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Gérer les deux formats de colonne (nom_course et nom)
            nom_col = row.get('nom', row.get('nom_course', '')).strip().lower()
            key = (nom_col, row['discipline'].strip().lower())
            metadata[key] = {
                'is_objectif': row['is_objectif'].strip().lower() == 'true',
                'saison': row['saison'].strip()
            }
    
    return metadata


def generate_metadata(output_path: str = "data/courses_metadata.csv", 
                     base_dir: str = "classements") -> None:
    """
    Génère le fichier courses_metadata.csv
    
    Args:
        output_path: Chemin du fichier de sortie
        base_dir: Répertoire contenant les courses
    """
    print("🔍 Scan des courses disponibles...")
    print("-" * 70)
    
    # Scanner les PDFs
    courses = scan_courses(base_dir)
    
    # Charger les métadonnées existantes (pour conserver is_objectif)
    existing_metadata = load_existing_metadata(output_path)
    
    print(f"   ✅ {len(courses)} courses trouvées")
    print()
    
    # Créer le fichier CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['nom', 'discipline', 'federation', 'is_objectif', 'saison'])
        
        for (nom, discipline), federation in sorted(courses.items()):
            # Récupérer les infos existantes ou valeurs par défaut
            existing = existing_metadata.get((nom, discipline), {})
            is_objectif = existing.get('is_objectif', False)
            saison = existing.get('saison', '25-26')
            
            writer.writerow([nom, discipline, federation, 
                           'true' if is_objectif else 'false', saison])
    
    print(f"✅ Fichier généré : {output_path}")
    print()
    
    # Statistiques
    cx_count = sum(1 for (_, disc) in courses.keys() if disc == 'cx')
    vtt_count = sum(1 for (_, disc) in courses.keys() if disc == 'vtt')
    route_count = sum(1 for (_, disc) in courses.keys() if disc == 'route')
    ufolep_count = sum(1 for fed in courses.values() if fed == 'ufolep')
    ffc_count = sum(1 for fed in courses.values() if fed == 'ffc')
    
    print("📊 Statistiques :")
    print(f"   • CX : {cx_count}")
    print(f"   • VTT : {vtt_count}")
    print(f"   • Route : {route_count}")
    print(f"   • UFOLEP : {ufolep_count}")
    print(f"   • FFC : {ffc_count}")
    print()
    
    # Afficher les courses objectif (préservées)
    objectifs = [(nom, disc) for (nom, disc), metadata in existing_metadata.items() 
                 if metadata.get('is_objectif')]
    
    if objectifs:
        print(f"⭐ {len(objectifs)} courses objectif préservées :")
        for nom, disc in sorted(objectifs):
            print(f"   • {nom} ({disc})")


if __name__ == "__main__":
    generate_metadata()
