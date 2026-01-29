# ECWM Challenge v3.0

Systeme de classement pour le challenge cyclo-cross de l'ECWM (Espoir Cycliste de Wambrechies-Marquette).

## Fonctionnalites

- **Extraction automatique** depuis les PDFs UFOLEP (CX et VTT)
- **Systeme de points moderne** base sur le percentile (equitable selon la taille du peloton)
- **Multi-disciplines** : Support CX, Route et VTT UFOLEP
- **Multi-federations** : Support UFOLEP et FFC avec coefficients differents
- **Bonus assiduite** : Paliers progressifs selon le nombre de courses
- **Courses objectif** : Bonus sur la participation pour encourager la presence
- **Site web statique** : Interface moderne pour consulter le classement
- **Configuration externalisee** : Tous les parametres dans des CSV

## Structure du projet

```
ufolep_extractor/
├── main.py                      # CLI unique avec sous-commandes
├── config/                      # Configuration
│   ├── points.csv               # Parametres du systeme
│   ├── courses.csv              # Metadonnees des courses
│   ├── coureurs.csv             # Liste des coureurs
│   ├── badges.csv               # Configuration badges
│   ├── sources_ffc.csv          # Sources FFC a scraper
│   ├── sources_manuelles.csv    # Sources saisies manuelles
│   ├── sources_ufolep.csv       # Sources UFOLEP a scraper
│   ├── coefficients_peloton.csv # Coefficients de reduction selon taille peloton
│   └── points_par_position.csv  # Points par position (sans nb participants)
├── src/
│   ├── core/                    # Modules centraux
│   │   ├── config.py            # Gestionnaire de configuration
│   │   ├── calculator.py        # Calculateur de points
│   │   ├── badges.py            # Systeme de badges
│   │   ├── models.py            # Modeles de donnees
│   │   └── utils.py             # Fonctions utilitaires
│   ├── parsers/                 # Parsers de fichiers
│   │   ├── ufolep.py            # Parser UFOLEP
│   │   ├── ffc_csv.py           # Parser FFC CSV
│   │   ├── manual.py            # Parser saisies manuelles
│   │   └── cartons.py           # Parser cartons/licences
│   └── scrapers/                # Scrapers web
│       └── ufolep_calendar.py   # Scraper calendrier UFOLEP
├── classements/                 # Donnees de resultats
│   ├── ufolep/
│   │   ├── cx-25-26/           # PDFs CX
│   │   └── vtt-25-26/          # PDFs VTT
│   ├── ffc/
│   │   ├── cx-25-26/           # CSV FFC CX
│   │   └── route-25-26/        # CSV FFC Route
│   └── saisies_manuelles.csv
├── cartons/                     # Licences PDF/Excel
├── cache/                       # Cache d'extraction
└── docs/                        # Site web genere
    ├── index.html
    ├── data.json
    └── assets/
```

## Utilisation

### Commandes disponibles

```bash
# Pipeline complet (defaut)
python main.py                    # Extraction + site (utilise le cache)
python main.py --skip-cache       # Forcer la reextraction

# Initialisation coureurs (une fois par saison)
python main.py init-coureurs      # Genere coureurs.csv depuis cartons/licences

# Synchronisation courses (quand nouvelles courses disponibles)
python main.py sync-courses              # Telecharge toutes les courses (FFC + UFOLEP)
python main.py sync-courses --ffc        # FFC uniquement
python main.py sync-courses --ufolep     # UFOLEP uniquement
python main.py sync-courses --force      # Forcer le re-telechargement
python main.py sync-courses --dry-run    # Apercu sans modification

# Serveur local
python main.py serve              # Serveur sur localhost:8000
python main.py serve --port 3000  # Serveur sur port 3000
```

### Workflow depuis zéro

```bash
# SETUP INITIAL (une fois par saison)
python main.py init-coureurs     # Genere coureurs.csv depuis cartons/
python main.py sync-courses      # Telecharge PDFs UFOLEP + scrape FFC + cree courses.csv

# CALCUL & PUBLICATION (apres chaque course)
python main.py                   # Pipeline complet -> docs/data.json
python main.py serve             # Test local sur localhost:8000

# DEPLOIEMENT
git push                         # GitHub Pages
```

### Workflow hebdomadaire (nouvelle course disponible)

```bash
# 1. Télécharger uniquement les NOUVEAUX résultats
python main.py sync-courses      # Le cache garde les anciens fichiers

# 2. Recalculer les points avec tous les résultats
python main.py                   # Pipeline complet

# 3. Vérifier localement
python main.py serve             # Test sur localhost:8000

# 4. Publier
git add .
git commit -m "ajout course X"
git push
```

**Note:** Le système de cache est intelligent :
- `sync-courses` ne télécharge que les nouveaux fichiers
- Les fichiers existants ne sont pas re-téléchargés
- Pour forcer le re-téléchargement : `sync-courses --force`

## Systeme de points

### Formule de base

```
Points = (Participation + Performance) x Coefficient
```

- **Participation** : 25 pts fixes pour finir la course
- **Performance** : 0-25 pts selon le percentile (classement relatif)
- **Coefficient** : Selon le type de course (CX/Route, UFOLEP/FFC)

### Reduction petites courses

Pour eviter les abus sur les petites courses, les **points de performance sont reduits** :

| Participants | Coefficient |
|--------------|-------------|
| 1-4          | 50%         |
| 5-9          | 75%         |
| 10+          | 100%        |

Configurable dans `config/paliers.csv`

### Courses objectif

Les courses objectif appliquent un bonus sur la participation :

```
Participation = 25 x 1.5 = 37.5 pts
```

### Coefficients par type de course

| Type | Coefficient |
|------|-------------|
| CX UFOLEP | 1.0 |
| Route UFOLEP | 1.0 |
| VTT UFOLEP | 1.0 |
| CX FFC | 0.75 |
| Route FFC | 0.6 |

## Systeme de badges

Badges de gamification calcules automatiquement :

**Types de badges :**
- **Badges a paliers** : Bronze/Argent/Or (Assidu, Competiteur)
- **Badges uniques** : Recompenses speciales (Multi-disciplines, Polyvalent)

**Criteres :**
- Nombre de courses completees
- Nombre de podiums (top 3)
- Nombre de top 10
- Courses objectif participees
- Percentile moyen
- Taux de participation
- Multi-federations (UFOLEP + FFC)
- Multi-disciplines (Route + CX/VTT)

Configuration dans `config/badges.csv`

## Configuration

Tous les parametres sont configurables via les fichiers CSV dans `config/` :

| Fichier | Description |
|---------|-------------|
| `points.csv` | Points de base, coefficients, bonus objectif |
| `coefficients_peloton.csv` | Coefficients de reduction selon taille du peloton |
| `badges.csv` | Configuration des badges et points bonus |
| `courses.csv` | Type, federation, et statut objectif de chaque course |
| `coureurs.csv` | Liste des coureurs et disciplines autorisees |
| `sources_manuelles.csv` | Sources de saisies manuelles (Google Sheets, CSV) |
| `sources_ffc.csv` | URLs FFC a scraper automatiquement |
| `sources_ufolep.csv` | URLs UFOLEP a scraper automatiquement |
| `points_par_position.csv` | Points par position (pour saisies sans nb participants) |

## Operations courantes

### Ajout de coureurs

1. Editer `config/coureurs.csv`
2. Ajouter une ligne avec le nom complet : `PRENOM NOM`
3. Relancer `python main.py`

### Ajout de nouveaux PDFs

1. Placer les PDFs dans `classements/ufolep/cx-25-26/` ou `vtt-25-26/`
2. Relancer `python main.py` (le cache detecte automatiquement les nouveaux PDFs)

### Forcer la reextraction

```bash
python main.py --skip-cache
```

### Vider le cache

```bash
rm -rf cache/
```

## Personnalisation du site

Les fichiers du site sont dans `docs/` :

- `assets/style.css` : Personnaliser les couleurs, polices
- `assets/app.js` : Modifier l'affichage
- `index.html` : Structure de la page

## Depannage

### Coureur non trouve dans un PDF

1. Verifier le nom exact dans le PDF
2. Ajouter dans `config/corrections.csv` si necessaire
3. Verifier que le nom dans `config/coureurs.csv` correspond

### PDF non parse correctement

1. Verifier que c'est un PDF UFOLEP standard
2. Utiliser `classements/saisies_manuelles.csv` en dernier recours

---

## Changelog

### v3.0.0 (29/01/2026)
- Refactoring complet : CLI unique avec sous-commandes (sync, init, serve)
- Renommage data/ -> config/ avec noms de fichiers simplifies
- Suppression de la generation CSV inutile
- Integration de tous les scripts dans main.py
- Nettoyage du dossier old/

### v2.1.0 (27/01/2026)
- Script `main.py` unifie avec cache intelligent
- Performance : 96% plus rapide apres la 1ere execution
- Badges integres dans le workflow principal

### v2.0.0 (25/01/2026)
- Systeme de points base sur le percentile
- Systeme de badges et gamification
- Support multi-disciplines et multi-federations
- Site web statique moderne

---

**Version** : 3.0.0
**Derniere mise a jour** : 29/01/2026
