# ECWM Challenge v2.0 🏆

Système de classement pour le challenge cyclo-cross de l'ECWM (Espoir Cycliste de Wambrechies-Marquette).

## 🎯 Fonctionnalités

- ✅ **Extraction automatique** depuis les PDFs UFOLEP (CX et VTT)
- ✅ **Système de points moderne** basé sur le percentile (équitable selon la taille du peloton)
- ✅ **Multi-disciplines** : Support CX, Route et VTT UFOLEP
- ✅ **Multi-fédérations** : Support UFOLEP et FFC avec coefficients différents
- ✅ **Bonus assiduité** : Paliers progressifs selon le nombre de courses
- ✅ **Courses objectif** : Bonus sur la participation pour encourager la présence
- ✅ **Site web statique** : Interface moderne pour consulter le classement
- ✅ **Configuration externalisée** : Tous les paramètres dans des CSV

## 📁 Structure du projet

```
├── src/                        # Code source
│   ├── parsers/               # Parsers de PDFs
│   │   ├── ufolep.py         # Parser UFOLEP (CX, VTT, Route)
│   │   ├── manual.py         # Parser saisies manuelles
│   │   └── cartons.py        # Parser cartons/licences
│   └── core/                 # Modules centraux
│       ├── config.py         # Gestionnaire de configuration
│       ├── calculator.py     # Calculateur de points
│       ├── models.py         # Modèles de données
│       ├── badges.py         # Système de badges
│       └── utils.py          # Fonctions utilitaires partagées
│
├── data/                      # Données et configuration
│   ├── config_points.csv     # Paramètres du système
│   ├── courses_metadata.csv  # Métadonnées des courses
│   ├── ecwm_coureurs.csv     # Liste des coureurs
│   ├── sources_config.csv    # Configuration saisies manuelles
│   ├── badges_config.csv     # Configuration badges
│   └── paliers_reduction.csv # Paliers de réduction
│
├── classements/               # PDFs des courses
│   └── ufolep/
│       ├── cx-25-26/         # Saison CX 2025-2026
│       └── vtt-25-26/        # Saison VTT 2025-2026
│
├── cache/                     # Cache pour performance 🚀
│   ├── extraction_data.json  # Cache des extractions PDFs
│   └── badges_data.json      # Cache des badges calculés
│
├── docs/                      # Site web statique
│   ├── index.html            # Page principale
│   ├── data.json             # Données du classement
│   └── assets/               # CSS et JS
│
├── main.py                   # 🎯 Script principal unifié (NOUVEAU)
├── extract_v2.py             # Script d'extraction (legacy, toujours fonctionnel)
├── generate_site.py          # Générateur de site (legacy, toujours fonctionnel)
├── serve.py                  # Serveur web local pour tests
└── old/                       # Ancien code (sauvegarde)
```

## 🚀 Utilisation

### ⚡ Méthode Rapide (Recommandée)

**Une seule commande pour tout faire :**

```bash
python3 main.py
```

Ce script unifié :
- ✅ Extrait les PDFs (CX, VTT, Route)
- ✅ Charge les saisies manuelles
- ✅ Calcule les points et badges
- ✅ Génère le CSV classement (`ecwm_classements.csv`)
- ✅ Génère le JSON site (`docs/data.json`)
- 🚀 **Cache intelligent** : Si rien n'a changé, utilise le cache (96% plus rapide!)

**Options disponibles :**

```bash
python3 main.py                 # Workflow complet (utilise le cache si valide)
python3 main.py --skip-cache    # Force la réextraction des PDFs
python3 main.py --extract-only  # Extraction uniquement (créer le cache)
python3 main.py --generate-only # Génération site uniquement (depuis le cache)
```

**💡 Performance :**
- **1ère exécution** : ~2 minutes (extraction complète)
- **Exécutions suivantes** : ~5 secondes (utilise le cache `cache/`)
- Le cache est automatiquement invalidé si les PDFs ou configs changent

---

### 📋 Workflows Détaillés (Optionnel)

#### 0. Générer la liste des coureurs (une fois par saison)

```bash
python3 generate_coureurs_list.py
```

Ce script :
- Parse les cartons UFOLEP (CX, Route, VTT) et licences FFC
- Extrait automatiquement les noms des coureurs
- Génère `data/ecwm_coureurs.csv` avec les disciplines autorisées par coureur
- Détecte automatiquement les coureurs multi-discipline et multi-fédération

**Fichiers sources** (à placer dans `old/data/cartons/`) :
- `carte CC WAMBRECHIES.pdf` : Carton CX UFOLEP
- `carte Route WAMBRECHIES.pdf` : Carton Route UFOLEP (optionnel)
- `cartes VTT WAMBRECHIES.pdf` : Carton VTT UFOLEP
- `Licences_ffc.pdf` : Licences FFC (seuls les "autorisé en compétition" sont extraits)

#### 1. Générer la liste des courses (après ajout de nouveaux PDFs)

```bash
python3 generate_courses_metadata.py
```

Ce script :
- Scanne tous les PDFs dans `classements/ufolep/cx-25-26/` et `classements/ufolep/vtt-25-26/`
- Génère automatiquement `data/courses_metadata.csv`
- **Préserve les courses objectif** déjà marquées
- Détecte automatiquement CX, VTT, UFOLEP, FFC

**📝 Note** : Lancer ce script dès que tu ajoutes de nouveaux PDFs dans `classements/`

#### 2. Méthode alternative (scripts séparés)

Si tu préfères exécuter les étapes séparément :

```bash
# Extraction uniquement
python3 extract_v2.py

# Génération site uniquement
python3 generate_site.py
```

**⚠️ Note** : Ces scripts sont conservés pour compatibilité mais **réexécutent tout le workflow** à chaque fois (pas de cache). Préférer `main.py`.

---

### 3. Tester le site en local

```bash
python3 serve.py
```

Ouvrir http://localhost:8000 dans un navigateur.

### 4. Publier sur GitHub Pages

```bash
# Committer les fichiers du site
git add docs/
git commit -m "Mise à jour du classement"
git push

# Configurer GitHub Pages pour pointer vers le dossier docs/
# (Paramètres du repo > Pages > Source : main branch, /site folder)
```

## 📊 Système de points

### Formule de base

```
Points = (Participation + Performance) × Coefficient
```

- **Participation** : 25 pts fixes pour finir la course
- **Performance** : 0-25 pts selon le percentile (classement relatif)
- **Coefficient** : Selon le type de course (CX/Route, UFOLEP/FFC)

### Réduction petites courses ⚠️

Pour éviter les abus sur les petites courses, les **points de performance sont réduits** :

| Participants | Coefficient |
|--------------|-------------|
| 1-4          | 50%         |
| 5-9          | 75%         |
| 10+          | 100% (pas de réduction) |

**Exemple** : 1er sur 3 participants
- Percentile réel : 100% (affiché tel quel)
- Points performance base : 25 pts
- Points performance appliqués : 25 × 0.50 = **12.5 pts**
- Les points de participation (25 pts) restent inchangés

💡 **Configurable** : Les paliers sont définis dans `data/paliers_reduction.csv`

### Courses objectif

Les courses objectif (⭐) appliquent un bonus **uniquement sur la participation** :

```
Participation = 25 × 1.5 = 37.5 pts
```

Cela encourage la présence sans amplifier les écarts de performance.

### Système de badges 🏅

Le système de badges de gamification est **calculé automatiquement** dans le workflow principal. Les badges apportent des bonus de points selon les performances :

**Types de badges :**
- **Badges à paliers** : Bronze/Argent/Or (exemple : Assidu, Compétiteur)
- **Badges uniques** : Récompenses spéciales (exemple : Multi-disciplines, Polyvalent)

**Critères de badges :**
- Nombre de courses complétées
- Nombre de podiums (top 3)
- Nombre de top 10
- Courses objectif participées
- Percentile moyen
- Taux de participation
- Multi-fédérations (UFOLEP + FFC)
- Multi-disciplines (Route + CX/VTT)

**Configuration** : Les badges sont configurables dans `data/badges_config.csv` (nom, emoji, critères, seuils, points bonus)

### Coefficients par type de course

| Type | Coefficient |
|------|-------------|
| CX UFOLEP | 1.0 |
| Route UFOLEP | 1.0 |
| VTT UFOLEP | 1.0 |
| CX FFC | 0.75 |
| Route FFC | 0.6 |

## ⚙️ Configuration

Tous les paramètres sont configurables via les fichiers CSV dans `data/` :

- `config_points.csv` : Points de base, coefficients, bonus objectif
- `paliers_reduction.csv` : Paliers de réduction pour petites courses
- `badges_config.csv` : Configuration des badges et points bonus
- `courses_metadata.csv` : Type, fédération, et statut objectif de chaque course
- `ecwm_coureurs.csv` : Liste des coureurs et disciplines autorisées

Voir `data/README.md` pour plus de détails.

## 🔧 Opérations courantes

### Ajout de coureurs

1. Éditer `data/ecwm_coureurs.csv`
2. Ajouter une ligne avec le nom complet en majuscules : `PRENOM NOM`
3. Relancer `python3 main.py`

### Ajout de nouveaux PDFs

1. Placer les PDFs dans `classements/ufolep/cx-25-26/` ou `vtt-25-26/`
2. (Optionnel) Lancer `python3 generate_courses_metadata.py` pour mettre à jour la liste des courses
3. Relancer `python3 main.py` (le cache détectera automatiquement les nouveaux PDFs)

### Forcer la réextraction

Si tu veux forcer la réextraction même si les fichiers n'ont pas changé :

```bash
python3 main.py --skip-cache
```

### Vider le cache

Le cache est stocké dans `cache/`. Pour le supprimer :

```bash
rm -rf cache/
```

**Note** : Le cache est automatiquement invalidé quand :
- Un PDF est ajouté/modifié dans `classements/`
- Un fichier de config est modifié dans `data/`

## 🎨 Personnalisation du site

Les fichiers du site sont dans `docs/` :

- `assets/style.css` : Personnaliser les couleurs, polices, etc.
- `assets/app.js` : Modifier l'affichage ou ajouter des fonctionnalités
- `index.html` : Structure de la page

## 🐛 Dépannage

### Coureur non trouvé dans un PDF

1. Vérifier le nom exact dans le PDF
2. Ajouter dans `data/corrections.csv` si nécessaire
3. Vérifier que le nom dans `ecwm_coureurs.csv` correspond

### PDF non parsé correctement

1. Vérifier que c'est un PDF UFOLEP standard
2. Utiliser `classements/saisies_manuelles.csv` en dernier recours

## 📈 Évolutions futures

Voir `TODO.md` pour la liste complète des fonctionnalités prévues :

- [ ] Parser FFC automatique
- [ ] Interface web de saisie manuelle
- [x] ✅ Gamification (badges, stats avancées)
- [x] ✅ Système de cache intelligent
- [ ] Graphiques d'évolution dans le temps
- [ ] Mode multi-saisons
- [ ] Export PDF du classement

## 🤝 Contribution

Créé avec ❤️ par [Claude Code](https://claude.com/claude-code)

---

## 🔄 Changelog

### v2.1.0 (27/01/2026)
- ✨ Nouveau script `main.py` unifié avec cache intelligent
- ⚡ Performance : 96% plus rapide après la 1ère exécution
- 🧹 Refactoring : Suppression de ~80 lignes de code dupliqué
- 🏅 Badges intégrés dans le workflow principal
- 🛠️ Création de `src/core/utils.py` pour les fonctions partagées

### v2.0.0 (25/01/2026)
- 🎯 Système de points basé sur le percentile
- 🏅 Système de badges et gamification
- 📊 Support multi-disciplines et multi-fédérations
- 🌐 Site web statique moderne

---

**Version** : 2.1.0
**Dernière mise à jour** : 27/01/2026
