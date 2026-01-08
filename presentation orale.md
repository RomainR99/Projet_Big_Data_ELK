# Présentation Orale - Projet Big Data
## Analyse de données Airbnb avec Elasticsearch et NLP

**Durée totale : 8 minutes**  
**Structure : 4 parties de 2 minutes chacune**

---

## 🎯 Partie 1 : Contexte et Objectif (2 minutes)

### Introduction
- **Problématique métier** : Analyser les données Airbnb pour identifier les risques d'investissement
- **Contexte** : Fusion de données de 2 villes (Bangkok + Barcelona)
- **Défi** : Analyser 48 000 annonces + 1,6 million de commentaires

### Objectifs du projet
1. **ETL** : Nettoyage et structuration des données
2. **Enrichissement** : Analyse NLP des commentaires pour extraire le sentiment
3. **Visualisation** : Dashboard interactif dans Kibana
4. **Valeur métier** : Identifier les appartements risqués même avec une note officielle correcte

### Stack technique
- **Elasticsearch 8.11.1** (moteur de recherche et d'analyse)
- **Kibana** (visualisation)
- **Python** (scripts ETL et NLP)
- **TextBlob** (analyse de sentiment)

### Points clés à retenir
- Un investisseur ne peut pas lire 1,6 million de commentaires
- Les notes officielles masquent parfois des problèmes récurrents
- Le NLP permet de détecter des signaux faibles (bruit, propreté, sécurité)

---

## 🔄 Partie 2 : Pipeline ETL et Ingestion (2 minutes)

### Étape 1 : Nettoyage et Fusion
- **Script** : `1_clean_data.py`
- **Actions** :
  - Fusion des 2 CSV (Bangkok + Barcelona)
  - Nettoyage des prix (suppression des $ et virgules)
  - Conversion des coordonnées en format `geo_point`
  - Ajout du champ `target_city` pour identifier l'origine
- **Résultat** : 48 216 annonces nettoyées → fichier Parquet

### Étape 2 : Injection dans Elasticsearch
- **Script** : `2_send_to_elk.py`
- **Méthode** : Bulk API avec `helpers.streaming_bulk`
- **Index créé** : `airbnb-listings`
- **Résultat** :
  - ✅ 48 216 documents indexés
  - ✅ 0 échec
  - ✅ Vérification : `_count` = 48 216

### Mapping Elasticsearch
- Champs clés configurés :
  - `location` : `geo_point` (pour les cartes)
  - `price` : `float`
  - `target_city` : `keyword` (pour les filtres)
  - `review_scores_rating` : `float`

### Points clés techniques
- Traitement par paquets (chunks) pour gérer le volume
- Validation des données après ingestion
- 2 villes distinctes : Bangkok (28 806) et Barcelona (19 410)

---

## 🧠 Partie 3 : Enrichissement NLP (2 minutes)

### Problématique
- **1,6 million de commentaires** à analyser
- Besoin de transformer du **texte libre** en **données quantifiables**

### Solution : Script NLP
- **Script** : `3_analyze_reviews.py`
- **Bibliothèque** : TextBlob
- **Processus** :
  1. Lecture par chunks (gestion mémoire)
  2. Calcul du **score de polarité** (-1 à +1)
  3. Attribution d'un **label** : Positif / Neutre / Négatif
  4. Indexation Bulk dans `airbnb-reviews`

### Résultats
- ✅ **1 602 423 reviews** analysées et indexées
- ✅ **0 échec** d'indexation
- ✅ Temps de traitement : quelques minutes

### Exemple concret
**Avant NLP :**
```
"Very noisy apartment, couldn't sleep"
```

**Après NLP :**
```json
{
  "comments": "Very noisy apartment, couldn't sleep",
  "sentiment_score": -0.62,
  "sentiment_label": "Negatif"
}
```

### Pourquoi TextBlob ?
- ✅ Rapide et léger (pas de GPU nécessaire)
- ✅ Pas d'entraînement requis
- ✅ Suffisant pour une analyse de sentiment globale
- ✅ Excellent compromis simplicité/performance

### Répartition des sentiments
- **Positif** : ~1 100 015 (68,7%)
- **Neutre** : ~476 983 (29,8%)
- **Négatif** : ~25 425 (1,6%)

---

## 📊 Partie 4 : Visualisations et Résultats (2 minutes)

### Visualisations créées dans Kibana

#### 1. Tag Cloud (Nuage de Mots)
- **Objectif** : Identifier les mots-clés récurrents dans les avis négatifs
- **Configuration** :
  - Champ : `comments`
  - Filtre : `sentiment_label = Negatif`
  - Exclusion des stopwords
- **Résultat** : Mots les plus fréquents (noise, dirty, small, stairs, cold)

#### 2. Camembert de Sentiment
- **Métrique** : Count
- **Dimension** : `sentiment_label`
- **Configuration** :
  - Time Filter : Last 5 years
  - Slice by : `sentiment_label`
- **Résultat** : Visualisation de la répartition globale

#### 3. Dashboard "Qualité Réelle"
- **Camembert** : Répartition Positif/Neutre/Négatif
- **Top Flops** : Appartements avec le plus de commentaires négatifs
- **Moteur de recherche** : Recherche de risques (bed bugs, scam, police)

### Problèmes rencontrés et solutions

#### Problème 1 : "No data" dans Lens
- **Cause** : Data View non rafraîchie
- **Solution** : Stack Management → Data Views → Refresh field list

#### Problème 2 : Champ `comments` non agrégable
- **Cause** : Champ `text` sans `fielddata` activé
- **Solution** : Activer `fielddata: true` dans le mapping

### Impact métier
- ✅ **Détection rapide** des appartements risqués
- ✅ **Analyse sémantique** au-delà des notes numériques
- ✅ **Identification de signaux faibles** (bruit, sécurité, propreté)
- ✅ **Décision d'investissement** plus éclairée

### Démonstration
- Un appartement peut avoir une note officielle de 4,5/5
- Mais contenir des commentaires négatifs récurrents sur le bruit
- Le NLP permet de détecter ce risque en quelques secondes

---

## 🎯 Conclusion (30 secondes)

### Récapitulatif
1. ✅ **ETL robuste** : 48K annonces nettoyées et indexées
2. ✅ **NLP efficace** : 1,6M commentaires enrichis avec sentiment
3. ✅ **Visualisations** : Dashboard interactif dans Kibana
4. ✅ **Valeur métier** : Identification de risques non visibles dans les notes

### Points forts
- Pipeline scalable et reproductible
- Traitement de gros volumes (1,6M documents)
- Analyse NLP pour enrichir les données structurées
- Visualisations exploitables pour la prise de décision

### Perspectives
- Parallélisation du traitement NLP
- Modèles plus avancés (VADER, spaCy)
- Intégration de données supplémentaires (météo, événements)
- Alertes automatiques sur les risques détectés

---

## 📝 Notes pour la présentation

### Timing recommandé
- **Partie 1** : 2 min (Contexte)
- **Partie 2** : 2 min (ETL)
- **Partie 3** : 2 min (NLP)
- **Partie 4** : 2 min (Visualisations)
- **Conclusion** : 30 sec


### Points à mettre en avant
- **Volumétrie** : 48K annonces + 1,6M reviews
- **Fiabilité** : 0 échec d'indexation
- **Performance** : Traitement en quelques minutes
- **Valeur métier** : Détection de risques non visibles

