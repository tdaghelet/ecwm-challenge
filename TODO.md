# TODO - Fonctionnalités futures

## 🎮 Gamification (Priorité moyenne)

### Statistiques par coureur
- [ ] Graphique d'évolution des points au fil des courses
- [ ] Meilleures performances (meilleur percentile, meilleure position)
- [ ] Statistiques par type de course (CX UFOLEP, FFC, etc.)
- [ ] Progression par rapport à la saison précédente

### Système de badges
- [ ] Badge "Assidu" : X courses effectuées
- [ ] Badge "Objectif" : Participer à toutes les courses objectifs
- [ ] Badge "Série" : X courses consécutives sans absence
- [ ] Badge "Podium" : X podiums dans la saison
- [ ] Badge "Top 10" : X top 10 dans la saison
- [ ] Badge "Warrior" : Finir toutes les courses (0 abandons)
- [ ] Badge "Multi-fédé" : Participer aux 2 fédérations

### Indicateurs de progression
- [ ] Prochains paliers de bonus : "Plus que 2 courses pour +100 pts !"
- [ ] Classement prévisionnel : "Si tu fais 3 courses à ~40 pts, tu passes 2e"
- [ ] Comparaison avec les autres : "Tu es à 50 pts du 3e"

### Leaderboards secondaires
- [ ] Meilleur percentile moyen
- [ ] Plus grand nombre de courses
- [ ] Meilleure progression (vs saison passée)
- [ ] Champion des courses objectif

---

## 📝 Interface de saisie manuelle (Priorité haute)

### Formulaire web local
- [ ] Interface HTML/JS qui tourne en local (Flask ou serveur Python simple)
- [ ] Formulaire pour saisir :
  - Nom de la course
  - Type : CX/Route, UFOLEP/FFC, Objectif oui/non
  - Liste des coureurs avec position et nb participants
- [ ] Validation des données
- [ ] Prévisualisation des points calculés

### Import depuis Excel/CSV
- [ ] Uploader un fichier Excel/CSV avec les résultats
- [ ] Mapper les colonnes automatiquement
- [ ] Valider et importer

---

## 🔧 Améliorations techniques

### Parser FFC
- [ ] Analyser le format des PDFs FFC
- [ ] Créer un parser spécifique `src/parsers/ffc.py`
- [ ] Détecter automatiquement UFOLEP vs FFC
- [ ] Tester sur des PDFs réels

### Multi-saisons
- [ ] Gérer plusieurs saisons dans l'interface
- [ ] Archiver les anciennes saisons
- [ ] Comparer les saisons entre elles
- [ ] Classement "all-time"

### Gestion des catégories
- [ ] Stocker la catégorie de chaque coureur (config)
- [ ] Filtrer le classement par catégorie
- [ ] Sous-classements par catégorie

---

## 🌐 Site web

### Features avancées
- [ ] Mode sombre / clair
- [ ] Recherche de coureur
- [ ] Filtres : par discipline, par fédération, par période
- [ ] Export PDF du classement
- [ ] Partage sur réseaux sociaux (image du classement)
- [ ] Page par coureur avec détail complet
- [ ] Calendrier des courses restantes
- [ ] Notifications : "Nouvelle course ajoutée !"

### PWA (Progressive Web App)
- [ ] Service worker pour mode hors ligne
- [ ] Installable sur mobile
- [ ] Notifications push (nouvelles courses)

---

## 📊 Analytics et insights

### Statistiques globales
- [ ] Taux de participation moyen par course
- [ ] Évolution du nombre de participants
- [ ] Courses les plus populaires
- [ ] Graphiques d'analyse

### Prédictions
- [ ] Prédire le classement final basé sur les courses restantes
- [ ] Suggestions personnalisées : "Va à cette course pour optimiser tes points"

---

## 🚀 Déploiement

### Automatisation
- [ ] GitHub Action pour générer le site automatiquement
- [ ] Script pour uploader les PDFs et regénérer
- [ ] Déploiement auto sur GitHub Pages

### Documentation
- [ ] Guide d'utilisation pour les coureurs
- [ ] Guide d'administration
- [ ] Documentation du système de points
- [ ] FAQ

---

**Dernière mise à jour** : 25/01/2026
