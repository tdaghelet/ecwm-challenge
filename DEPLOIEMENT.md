# Guide de déploiement sur GitHub Pages 🚀

## Prérequis

- Un compte GitHub
- Git installé sur votre machine

## Étapes de déploiement

### 1. Créer un dépôt GitHub

1. Aller sur https://github.com/new
2. Nom du repo : `ecwm-challenge` (ou autre)
3. Visibilité : Public ou Privé (selon votre choix)
4. Ne pas initialiser avec README (on a déjà tout)
5. Créer le repo

### 2. Initialiser Git localement

```bash
cd /chemin/vers/ufolep_extractor

# Initialiser git si pas déjà fait
git init

# Ajouter tous les fichiers
git add .

# Premier commit
git commit -m "Initial commit - ECWM Challenge v2.0"

# Lier au repo GitHub (remplacer USERNAME et REPO)
git remote add origin https://github.com/USERNAME/REPO.git

# Pousser
git push -u origin main
```

### 3. Activer GitHub Pages

1. Aller dans les **Settings** du repo
2. Menu **Pages** (à gauche)
3. **Source** :
   - Branch : `main`
   - Folder : `/site`
4. Sauvegarder
5. Attendre quelques minutes

Votre site sera accessible à :
```
https://USERNAME.github.io/REPO/
```

## Workflow de mise à jour

### Après chaque nouvelle course

1. **Ajouter le PDF** dans `classements/ufolep/cx-25-26/`

2. **Mettre à jour les métadonnées** si nouvelle course :
   ```bash
   # Éditer data/courses_metadata.csv
   # Ajouter une ligne pour la nouvelle course
   ```

3. **Générer le classement et le site** :
   ```bash
   python3 generate_site.py
   ```

4. **Vérifier localement** :
   ```bash
   python3 serve.py
   # Ouvrir http://localhost:8000
   ```

5. **Publier** :
   ```bash
   git add .
   git commit -m "Ajout course XXX"
   git push
   ```

6. **Attendre 1-2 minutes** que GitHub Pages se mette à jour

## Automatisation (optionnel)

### GitHub Action pour auto-déploiement

Créer `.github/workflows/deploy.yml` :

```yaml
name: Déploiement automatique

on:
  push:
    paths:
      - 'classements/**'
      - 'data/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'

      - name: Installer dépendances
        run: |
          pip install pandas pdfplumber

      - name: Générer le site
        run: python3 generate_site.py

      - name: Commit et push
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add site/
          git commit -m "Auto-update classement" || echo "No changes"
          git push
```

Avec ça, dès que tu push un nouveau PDF, le site se régénère automatiquement !

## Domaine personnalisé (optionnel)

### Si tu as un nom de domaine

1. Settings > Pages > Custom domain
2. Entrer ton domaine (ex: `challenge.ecwm.fr`)
3. Ajouter un CNAME chez ton registrar pointant vers `USERNAME.github.io`

## Sécurité

### Si les noms de coureurs sont privés

1. Mettre le repo en **Private**
2. GitHub Pages fonctionne quand même
3. Seules les personnes avec accès au repo verront le site

OU

2. Créer une page de login simple (JavaScript)
3. Protéger l'accès avec un mot de passe

## Dépannage

### Le site n'apparaît pas

- Vérifier que GitHub Pages est activé
- Vérifier que le dossier source est bien `/site`
- Attendre 5 minutes (propagation DNS)
- Vider le cache du navigateur

### Erreur 404

- Vérifier que `site/index.html` existe
- Vérifier que les chemins dans le HTML sont relatifs (`assets/style.css` et non `/assets/style.css`)

### Le site est vide

- Vérifier que `site/data.json` existe et contient des données
- Ouvrir la console du navigateur (F12) pour voir les erreurs

## Support

En cas de problème, consulter :
- [Documentation GitHub Pages](https://docs.github.com/pages)
- [Guide Git](https://git-scm.com/doc)

---

**Bon déploiement ! 🚀**
