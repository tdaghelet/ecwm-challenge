#!/usr/bin/env python3
"""
Synchronisation du calendrier UFOLEP

Script CLI pour :
- Récupérer le calendrier UFOLEP (CX + VTT)
- Télécharger les nouveaux PDFs
- Mettre à jour courses_metadata.csv avec les dates

Usage:
    python3 sync_ufolep.py                    # Sync complète
    python3 sync_ufolep.py --dry-run          # Voir ce qui serait fait
    python3 sync_ufolep.py --force            # Retélécharger tous les PDFs
    python3 sync_ufolep.py --discipline cx    # CX uniquement
"""
import argparse
import sys

from src.scrapers.ufolep_calendar import UfolepCalendarScraper


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Synchronisation du calendrier UFOLEP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python3 sync_ufolep.py                     # Sync complète (CX + VTT)
  python3 sync_ufolep.py --dry-run           # Aperçu sans téléchargement
  python3 sync_ufolep.py --force             # Retélécharger tous les PDFs
  python3 sync_ufolep.py --discipline cx     # CX uniquement
  python3 sync_ufolep.py --discipline vtt    # VTT uniquement
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Afficher les actions sans les exécuter"
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help="Forcer le retéléchargement de tous les PDFs"
    )

    parser.add_argument(
        '--discipline',
        choices=['cx', 'vtt'],
        help="Synchroniser une seule discipline"
    )

    parser.add_argument(
        '--saison',
        default='25-26',
        help="Saison à synchroniser (défaut: 25-26)"
    )

    parser.add_argument(
        '--output-dir',
        default='classements/ufolep',
        help="Répertoire de destination des PDFs (défaut: classements/ufolep)"
    )

    args = parser.parse_args()

    print("\n")
    print("=" * 70)
    print("       SYNCHRONISATION CALENDRIER UFOLEP")
    print("=" * 70)

    if args.dry_run:
        print("[MODE DRY-RUN - Aucune modification ne sera effectuée]")

    # Créer le scraper
    scraper = UfolepCalendarScraper()

    # Si une discipline spécifique est demandée
    if args.discipline:
        print(f"\nSynchronisation {args.discipline.upper()} uniquement")
        entries = scraper.scrape_calendar(args.discipline)

        if args.dry_run:
            print(f"\n[DRY RUN] {len(entries)} courses trouvées:")
            for entry in entries:
                status = "PDF" if entry.pdf_url else "Pas de PDF"
                print(f"   - {entry.date}: {entry.lieu} [{status}]")
        else:
            # Télécharger
            output_dir = f"{args.output_dir}/{args.discipline}-{args.saison}"
            scraper.download_pdfs(entries, output_dir, force=args.force)
            # Mettre à jour les métadonnées
            scraper.update_courses_metadata(entries)

    else:
        # Sync complète (CX + VTT)
        all_entries = scraper.run_full_sync(
            output_base_dir=args.output_dir,
            saison=args.saison,
            force_download=args.force,
            dry_run=args.dry_run
        )

        # Résumé
        total_cx = len(all_entries.get('cx', []))
        total_vtt = len(all_entries.get('vtt', []))

        print("\n" + "=" * 70)
        print("RÉSUMÉ")
        print("=" * 70)
        print(f"   Courses CX trouvées:  {total_cx}")
        print(f"   Courses VTT trouvées: {total_vtt}")
        print(f"   Total:                {total_cx + total_vtt}")

        if args.dry_run:
            print("\n[DRY RUN] Aucun fichier n'a été modifié.")
        else:
            print("\nFichiers générés:")
            print(f"   - PDFs dans: {args.output_dir}/{{cx,vtt}}-{args.saison}/")
            print(f"   - Métadonnées: data/courses_metadata.csv")

    print("\nTerminé!")
    print("=" * 70)


if __name__ == "__main__":
    main()
