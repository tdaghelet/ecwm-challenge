# Configuration du système de points ECWM

## 📁 Structure des fichiers

### config_points.csv
Paramètres du système de calcul de points.

**Colonnes** :
- `parametre` : Nom du paramètre
- `valeur` : Valeur numérique
- `description` : Explication

**Paramètres disponibles** :
- `points_participation` : Points fixes pour participer (actuellement 25)
- `points_performance_max` : Points max pour performance (actuellement 25)
- `coef_cx_ufolep` : Coefficient CX UFOLEP (1.0 = référence)
- `coef_route_ufolep` : Coefficient Route UFOLEP (1.0)
- `coef_cx_ffc` : Coefficient CX FFC (0.75)
- `coef_route_ffc` : Coefficient Route FFC (0.6)
- `bonus_objectif` : Multiplicateur courses objectif (1.5 = +50%)

---


### courses_metadata.csv
Métadonnées de chaque course.

**Génération** : Fichier **généré automatiquement** via `generate_courses_metadata.py` qui scanne les PDFs dans `classements/`.

**Colonnes** :
- `nom_course` : Nom de la course (sans numéro, minuscules)
- `discipline` : `cx` (cyclo-cross), `route`, ou `vtt` (VTT)
- `federation` : `ufolep` ou `ffc`
- `is_objectif` : `true` si course objectif club, `false` sinon
- `saison` : Saison (ex: `25-26`)

**Workflow** :
1. Ajouter les PDFs dans `classements/ufolep/cx-25-26/` ou `classements/ufolep/vtt-25-26/`
2. Lancer `python3 generate_courses_metadata.py`
3. Le fichier est régénéré en préservant les courses objectif déjà marquées
4. Marquer manuellement les courses objectif si nécessaire (`is_objectif=true`)

**Exemple** : `halluin,cx,ufolep,true,25-26`

---

### ecwm_coureurs.csv
Liste des coureurs du club ECWM avec leurs disciplines autorisées.

**Colonnes** :
- `COUREUR` : Nom complet (PRENOM NOM)
- `ufolep_cx` : 1 si autorisé en CX UFOLEP, 0 sinon
- `ufolep_route` : 1 si autorisé en Route UFOLEP, 0 sinon
- `ufolep_vtt` : 1 si autorisé en VTT UFOLEP, 0 sinon
- `ffc_cx` : 1 si licencié FFC (autorisé CX), 0 sinon
- `ffc_route` : 1 si licencié FFC (autorisé Route), 0 sinon

**Génération** : Fichier généré automatiquement via `generate_coureurs_list.py` qui parse :
- Carton CX UFOLEP (`old/data/cartons/carte CC WAMBRECHIES.pdf`)
- Carton Route UFOLEP (si disponible)
- Carton VTT UFOLEP (`old/data/cartons/cartes VTT WAMBRECHIES.pdf`)
- Licences FFC (`old/data/cartons/Licences_ffc.pdf`) - uniquement les coureurs "autorisé en compétition"

**Note** : Les coureurs licenciés FFC peuvent participer en CX et Route (pas de VTT en FFC).

---

### ecwm_coureurs.csv
Liste des coureurs du club ECWM.

**Colonnes** :
- `COUREUR` : Nom complet en majuscules (PRENOM NOM)

**Note** : Les noms sont automatiquement normalisés pour le matching.

---

### badges_config.csv
Configuration des badges de gamification.

**Colonnes** :
- `badge_id` : Identifiant unique du badge
- `nom` : Nom affiché du badge
- `emoji` : Emoji représentant le badge
- `description` : Description du badge
- `type` : `palier` (plusieurs niveaux) ou `unique` (un seul niveau)
- `critere` : Critère d'obtention (nb_courses, nb_podiums, nb_top10, nb_courses_objectif, nb_abandons, deux_federations, deux_disciplines, percentile_moyen, taux_participation)
- `niveau` : Niveau du badge (Bronze, Argent, Or, Platine, Diamant) pour type `palier`, vide ou "Unique" sinon
- `seuil` : Valeur seuil pour obtenir le badge (nombre ou pourcentage)
- `actif` : `1` pour activer le badge, `0` pour le désactiver
- `bonus_points` : Points bonus accordés pour ce badge (0 pour les badges purement décoratifs)

**Critères disponibles** :
- `nb_courses` : Nombre de courses effectuées
- `nb_podiums` : Nombre de podiums (positions 1-3)
- `nb_top10` : Nombre de top 10
- `nb_courses_objectif` : Nombre de courses objectif effectuées
- `nb_abandons` : Nombre d'abandons
- `deux_federations` : Participer aux deux fédérations UFOLEP et FFC (seuil = 100)
- `deux_disciplines` : Participer aux deux disciplines CX et Route (seuil = 100)
- `percentile_moyen` : Percentile moyen minimum (seuil = pourcentage)
- `taux_participation` : Taux de participation aux courses de la saison (seuil = pourcentage)

**Exemple** : Un coureur avec 12 courses obtient le badge "Assidu Argent" (seuil 10)

---

## 🔧 Formule de calcul

```
Points_course = (pts_participation + pts_performance) × coef_type × bonus_objectif

Où :
- pts_participation = config["points_participation"]
- pts_performance = config["points_performance_max"] × percentile
- percentile = (nb_participants - position + 1) / nb_participants
- coef_type = config["coef_{discipline}_{federation}"]
- bonus_objectif = config["bonus_objectif"] si course objectif, sinon 1.0

Points_total = Σ(Points_course) + bonus_assiduité + bonus_badges

Où :
- bonus_badges = Σ(bonus_points des badges obtenus)
```

## 📊 Exemples

**Coureur A : 10e sur 35 coureurs en CX UFOLEP normal**
- Percentile : (35-10+1)/35 = 74.3%
- pts_participation : 25
- pts_performance : 25 × 0.743 = 18.6
- coef_type : 1.0 (CX UFOLEP)
- bonus_objectif : 1.0 (course normale)
- **Points : (25 + 18.6) × 1.0 × 1.0 = 43.6 pts**

**Coureur B : 5e sur 30 coureurs en CX FFC objectif**
- Percentile : (30-5+1)/30 = 86.7%
- pts_participation : 25
- pts_performance : 25 × 0.867 = 21.7
- coef_type : 0.75 (CX FFC)
- bonus_objectif : 1.5 (course objectif)
- **Points : (25 + 21.7) × 0.75 × 1.5 = 52.5 pts**
