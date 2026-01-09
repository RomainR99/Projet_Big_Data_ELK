# Présentation Orale - Projet Big Data
## Analyse de données Airbnb avec Elasticsearch et NLP

**Durée totale : 9 minutes**  
**Structure : 4 parties principales + conclusion**

- Partie 1 : Contexte et Objectif 
- Partie 2 : Pipeline ETL et Ingestion 
- Partie 3 : Enrichissement NLP 
- Partie 4 : Visualisations et Résultats 
- Conclusion : Récapitulatif et Perspectives 

---

## 🎯 Partie 1 : Contexte et Objectif 

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

## 🔄 Partie 2 : Pipeline ETL et Ingestion

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
  - `location` : `geo_point` ⭐ **Essentiel pour la cartographie** (visualisation Maps)
  - `price` : `float` (pour analyses financières)
  - `target_city` : `keyword` (pour filtres et comparaisons)
  - `review_scores_rating` : `float` (notes officielles)
  
**Note** : Le type `geo_point` permet de créer des cartes interactives dans Kibana Maps, ce qui est crucial pour l'analyse géographique.

### Points clés techniques
- Traitement par paquets (chunks) pour gérer le volume
- Validation des données après ingestion
- 2 villes distinctes : Bangkok (28 806) et Barcelona (19 410)

---

## 🧠 Partie 3 : Enrichissement NLP 

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

## 📊 Partie 4 : Visualisations et Résultats 

### A. Visualisations NLP - Analyse de Sentiment

#### 1. Tag Cloud (Nuage de Mots)
- **Objectif** : Identifier les mots-clés récurrents dans les avis négatifs
- **Résultat** : Mots les plus fréquents (noise, dirty, small, stairs, cold)
- **Valeur** : Détection rapide des problèmes récurrents

#### 2. Camembert de Sentiment
- **Répartition globale** : Positif (68,7%), Neutre (29,8%), Négatif (1,6%)
- **Configuration** : Time Filter Last 5 years, Slice by `sentiment_label`
- **Impact** : Vue d'ensemble immédiate de la satisfaction

#### 3. Dashboard "Qualité Réelle"
- **Camembert** : Répartition sentimentale
- **Top Flops** : Appartements avec le plus de commentaires négatifs
- **Moteur de recherche** : Recherche de risques (bed bugs, scam, police)

### B. Cartographie Immobilière (Maps)

**Objectif** : Visualiser géographiquement la répartition des prix

- **Carte interactive** avec coloration dynamique par prix
- **Palette de couleurs** : Vert (pas cher) → Rouge (cher)
- **Info-bulles** : Nom et prix au survol
- **Livrable** : "Carte des Prix Airbnb" permettant d'identifier les zones de tension

**Valeur métier** : La localisation est le critère #1 en immobilier. Cette carte permet aux investisseurs de maîtriser le terrain et les zones stratégiques.

### C. Statistiques Financières (Lens)

#### 1. Comparateur de Villes (Bar Chart)
- **Question** : Quelle ville est la plus chère en moyenne ?
- **Résultat** : Barcelona est plus chère que Bangkok (après conversion EUR)
- **Point technique** : Conversion THB → EUR (taux 36.6) pour comparer équitablement

#### 2. Distribution des Prix (Histogramme)
- **Objectif** : Identifier la gamme de prix standard
- **Détection** : Valeurs extrêmes (luxe ou erreurs de données)
- **Utilité** : Comprendre la structure du marché

#### 3. Répartition par Type (Donut Chart)
- **Question** : Le marché est-il dominé par les logements entiers ou chambres privées ?
- **Segmentation** : Entire home/apt vs Private room vs Shared room
- **Analyse** : Comprendre l'offre disponible par ville

### D. Conversion des Prix en Euros

**Défi technique** : Comparer Bangkok (THB) et Barcelona (EUR)

- **Solution** : Réindexation avec script Painless
- **Conversion** : Bangkok → EUR (divisé par 36.6)
- **Résultat** : Nouvel index `airbnb-listings-view` avec champ `price_eur` normalisé
- **Impact** : Comparaisons équitables entre villes

### Problèmes rencontrés et solutions

- **"No data" dans Lens** → Refresh Data View
- **Champ `comments` non agrégable** → Activer `fielddata: true`
- **Prix non comparables** → Conversion en euros avec réindexation

### Impact métier global
- ✅ **Analyse géographique** : Identification des zones stratégiques
- ✅ **Analyse financière** : Comparaison équitable entre villes
- ✅ **Analyse sémantique** : Détection de risques non visibles
- ✅ **Dashboard complet** : Vue d'ensemble multi-dimensionnelle

---

## 🎯 Conclusion 

### Récapitulatif complet du projet
1. ✅ **ETL robuste** : 48K annonces nettoyées et indexées (Bangkok + Barcelona)
2. ✅ **NLP efficace** : 1,6M commentaires enrichis avec sentiment (Positif/Neutre/Négatif)
3. ✅ **Visualisations multi-dimensionnelles** :
   - **NLP** : Tag Cloud, Camembert de Sentiment, Dashboard Qualité Réelle
   - **Géographie** : Carte interactive des prix avec coloration dynamique
   - **Finance** : Comparaison villes, Distribution prix, Répartition par type
4. ✅ **Normalisation des données** : Conversion THB → EUR pour comparaisons équitables
5. ✅ **Valeur métier** : Identification de risques et opportunités d'investissement

### Points forts techniques
- **Pipeline scalable** : ETL → NLP → Visualisation
- **Traitement de gros volumes** : 48K annonces + 1,6M reviews
- **Enrichissement intelligent** : NLP pour transformer texte en données quantifiables
- **Visualisations exploitables** : Maps, Lens, Dashboards interactifs
- **Normalisation des devises** : Script Painless pour conversion automatique

### Valeur ajoutée pour l'investisseur
- **Analyse géographique** : Identification des zones stratégiques et zones de tension
- **Analyse financière** : Comparaison équitable entre villes après conversion
- **Analyse sémantique** : Détection de risques non visibles dans les notes officielles
- **Vue d'ensemble** : Dashboard complet pour prise de décision éclairée

### Perspectives d'évolution
- **Performance** : Parallélisation du traitement NLP (multiprocessing)
- **Précision** : Modèles plus avancés (VADER, spaCy, transformers)
- **Enrichissement** : Intégration données supplémentaires (météo, événements, transports)
- **Automatisation** : Alertes automatiques sur risques détectés
- **Temps réel** : Streaming de nouvelles reviews pour analyse continue

---

## 📝 Notes pour la présentation

### Timing recommandé
- **Partie 1** : 2 min (Contexte et Objectif)
- **Partie 2** : 2 min (Pipeline ETL et Ingestion)
- **Partie 3** : 2 min (Enrichissement NLP)
- **Partie 4** : 2 min (Visualisations multi-dimensionnelles)
  - A. Visualisations NLP (30 sec)
  - B. Cartographie Immobilière (30 sec)
  - C. Statistiques Financières (45 sec)
  - D. Conversion prix + Problèmes/Solutions (15 sec)
- **Conclusion** : 1 min (Récapitulatif et Perspectives)


### Points à mettre en avant

#### Chiffres clés
- **Volumétrie** : 48K annonces + 1,6M reviews
- **Fiabilité** : 0 échec d'indexation
- **Performance** : Traitement en quelques minutes
- **Enrichissement** : 3 dimensions (NLP, Géographie, Finance)

#### Valeur métier
- **Analyse géographique** : Carte interactive des zones stratégiques
- **Analyse financière** : Comparaison équitable entre villes (normalisation EUR)
- **Analyse sémantique** : Détection de risques non visibles dans les notes
- **Dashboard complet** : Vue d'ensemble multi-dimensionnelle pour investisseurs

#### Innovation technique
- **Pipeline ETL** : Traitement par chunks, validation robuste
- **NLP TextBlob** : Analyse de sentiment à grande échelle
- **Réindexation intelligente** : Script Painless pour conversion de devises
- **Visualisations avancées** : Maps, Lens, Dashboards interactifs

### Structure de démonstration suggérée

1. **Introduction** : Montrer la problématique (note 4,5/5 mais commentaires négatifs)
2. **Pipeline ETL** : Afficher les statistiques d'ingestion
3. **NLP** : Montrer transformation avant/après (texte → sentiment)
4. **Cartographie** : Démontrer la carte interactive avec zones de prix
5. **Statistiques** : Présenter les 3 graphiques financiers (comparaison, distribution, répartition)
6. **Dashboard** : Vue d'ensemble complète
7. **Conclusion** : Synthèse valeur ajoutée pour l'investisseur

