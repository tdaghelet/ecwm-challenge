#!/usr/bin/env python3
"""
Génère la liste des coureurs ECWM avec leurs disciplines autorisées

Parse automatiquement :
- Carton CX UFOLEP
- Carton Route UFOLEP (si disponible)
- Carton VTT UFOLEP
- Licences FFC (autorisés en compétition)

Génère : data/ecwm_coureurs.csv
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Set
from src.parsers.cartons import CartonParser


def generate_coureurs_list(
    carton_cx: str = "old/data/cartons/carte CC WAMBRECHIES.pdf",
    carton_route: str = None,  # À ajouter si disponible
    carton_vtt: str = "old/data/cartons/cartes VTT WAMBRECHIES.pdf",
    licences_ffc: str = "old/data/cartons/Liste_Licencies.xlsx",
    output_file: str = "data/ecwm_coureurs.csv"
):
    """
    Génère la liste des coureurs avec leurs disciplines

    Args:
        carton_cx: Chemin vers le carton CX UFOLEP
        carton_route: Chemin vers le carton Route UFOLEP (optionnel)
        carton_vtt: Chemin vers le carton VTT UFOLEP
        licences_ffc: Chemin vers les licences FFC
        output_file: Fichier CSV de sortie
    """
    print("🏁 Génération de la liste des coureurs ECWM")
    print("=" * 70)
    print()

    parser = CartonParser()
    coureurs_dict: Dict[str, Dict[str, bool]] = {}

    # Parser CX UFOLEP
    if Path(carton_cx).exists():
        print(f"📄 Parsing {carton_cx}")
        coureurs_cx = parser.parse_carton_ufolep(carton_cx)
        print(f"   ✅ {len(coureurs_cx)} coureurs trouvés")

        for coureur in coureurs_cx:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False,
                    'ufolep_route': False,
                    'ufolep_vtt': False,
                    'ffc_cx': False,
                    'ffc_route': False
                }
            coureurs_dict[coureur.nom_complet]['ufolep_cx'] = True

    # Parser Route UFOLEP
    if carton_route and Path(carton_route).exists():
        print(f"📄 Parsing {carton_route}")
        coureurs_route = parser.parse_carton_ufolep(carton_route)
        print(f"   ✅ {len(coureurs_route)} coureurs trouvés")

        for coureur in coureurs_route:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False,
                    'ufolep_route': False,
                    'ufolep_vtt': False,
                    'ffc_cx': False,
                    'ffc_route': False
                }
            coureurs_dict[coureur.nom_complet]['ufolep_route'] = True

    # Parser VTT UFOLEP
    if Path(carton_vtt).exists():
        print(f"📄 Parsing {carton_vtt}")
        coureurs_vtt = parser.parse_carton_ufolep(carton_vtt)
        print(f"   ✅ {len(coureurs_vtt)} coureurs trouvés")

        for coureur in coureurs_vtt:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False,
                    'ufolep_route': False,
                    'ufolep_vtt': False,
                    'ffc_cx': False,
                    'ffc_route': False
                }
            coureurs_dict[coureur.nom_complet]['ufolep_vtt'] = True

    # Parser FFC
    if Path(licences_ffc).exists():
        print(f"📄 Parsing {licences_ffc}")
        coureurs_ffc = parser.parse_licences_ffc(licences_ffc)
        print(f"   ✅ {len(coureurs_ffc)} coureurs trouvés")

        for coureur in coureurs_ffc:
            if coureur.nom_complet not in coureurs_dict:
                coureurs_dict[coureur.nom_complet] = {
                    'ufolep_cx': False,
                    'ufolep_route': False,
                    'ufolep_vtt': False,
                    'ffc_cx': False,
                    'ffc_route': False
                }
            # En FFC, les coureurs peuvent faire CX et Route
            coureurs_dict[coureur.nom_complet]['ffc_cx'] = True
            coureurs_dict[coureur.nom_complet]['ffc_route'] = True

    print()
    print("📊 Génération du fichier CSV")
    print("-" * 70)

    # Créer le DataFrame
    rows = []
    for nom_complet, disciplines in sorted(coureurs_dict.items()):
        rows.append({
            'COUREUR': nom_complet,
            'ufolep_cx': 1 if disciplines['ufolep_cx'] else 0,
            'ufolep_route': 1 if disciplines['ufolep_route'] else 0,
            'ufolep_vtt': 1 if disciplines['ufolep_vtt'] else 0,
            'ffc_cx': 1 if disciplines['ffc_cx'] else 0,
            'ffc_route': 1 if disciplines['ffc_route'] else 0
        })

    df = pd.DataFrame(rows)

    # Sauvegarder
    df.to_csv(output_file, index=False)

    print(f"   ✅ Fichier généré: {output_file}")
    print(f"   📊 {len(df)} coureurs au total")
    print()

    # Statistiques
    print("📈 Statistiques")
    print("-" * 70)
    print(f"   UFOLEP CX   : {df['ufolep_cx'].sum()} coureurs")
    print(f"   UFOLEP Route: {df['ufolep_route'].sum()} coureurs")
    print(f"   UFOLEP VTT  : {df['ufolep_vtt'].sum()} coureurs")
    print(f"   FFC CX      : {df['ffc_cx'].sum()} coureurs")
    print(f"   FFC Route   : {df['ffc_route'].sum()} coureurs")
    print()

    # Badges potentiels
    multi_ufolep = df[(df['ufolep_cx'] == 1) & ((df['ufolep_route'] == 1) | (df['ufolep_vtt'] == 1))]['COUREUR'].tolist()
    multi_fede = df[(df[['ufolep_cx', 'ufolep_route', 'ufolep_vtt']].sum(axis=1) > 0) & (df[['ffc_cx', 'ffc_route']].sum(axis=1) > 0)]['COUREUR'].tolist()

    print("🏅 Potentiel pour badges")
    print("-" * 70)
    print(f"   Multi-discipline UFOLEP: {len(multi_ufolep)} coureurs")
    if multi_ufolep:
        for coureur in multi_ufolep[:5]:
            print(f"      - {coureur}")
        if len(multi_ufolep) > 5:
            print(f"      ... et {len(multi_ufolep) - 5} autres")

    print(f"\n   Multi-fédération       : {len(multi_fede)} coureurs")
    if multi_fede:
        for coureur in multi_fede[:5]:
            print(f"      - {coureur}")
        if len(multi_fede) > 5:
            print(f"      ... et {len(multi_fede) - 5} autres")

    print()
    print("✅ Terminé !")
    print("=" * 70)


if __name__ == "__main__":
    generate_coureurs_list()
