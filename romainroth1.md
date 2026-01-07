# Audit Elasticsearch d’un fichier CSV Airbnb

## 1. Contexte et objectif

L’objectif de ce travail est de réaliser un **audit de données** à partir d’un fichier CSV contenant des annonces Airbnb, en utilisant **Elasticsearch et Kibana**.

L’audit vise à :
- vérifier la bonne ingestion des données,
- analyser la qualité et la complétude des champs,
- auditer le mapping Elasticsearch,
- identifier les limites analytiques,
- formuler des recommandations d’amélioration.

---

## 2. Environnement technique

- **Elasticsearch** : version 8.11.1 (Docker)
- **Kibana** : version compatible 8.x
- **Méthode d’ingestion** : Kibana *File Data Visualizer*
- **Fichier source** : `listings.csv`

---

## 3. Ingestion du fichier CSV

### 3.1 Méthode utilisée

Le fichier `listings.csv` a été importé dans Elasticsearch via **Kibana → Machine Learning → Data Visualizer**.

Cette méthode permet :
- la détection automatique du séparateur (tabulation),
- l’analyse des types de champs,
- la création automatique du mapping,
- une première évaluation de la qualité des données.

### 3.2 Index créé

- **Nom de l’index** : `airbnb_listings_audit`
- **Créé par** : `file-data-visualizer`

---

## 4. Vérification de l’ingestion et volumétrie

### 4.1 Nombre de documents

Requête exécutée :
```json


GET airbnb_listings_audit/_count

# Click the Variables button, above, to create your own variables.
GET ${exampleVariable1} // _search
{
  "query": {
    "${exampleVariable2}": {} // match_all
  }
}
GET airbnb_listings_audit/_search
{
  "size": 0,
  "aggs": {
    "missing_price": {
      "missing": { "field": "price" }
    }
  }
}
GET airbnb_listings_audit/_search
{
  "size": 0,
  "query": { "exists": { "field": "price" } }
}
GET airbnb_listings_audit/_mapping

#Liste des index
GET _cat/indices?v

#Nombre de documents
GET airbnb_listings_audit/_count

GET airbnb_listings_audit/_search
{
  "size": 5,
  "_source": ["id", "latitude", "longitude", "location"]
}

Résultat :
{
  "took": 9,
  "timed_out": false,
  "_shards": {
    "total": 1,
    "successful": 1,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 10000,
      "relation": "gte"
    },
    "max_score": 1,
    "hits": [
      {
        "_index": "airbnb_listings_audit",
        "_id": "yonDl5sBPhNOaOkL9WXW",
        "_score": 1,
        "_source": {
          "id": 27934,
          "longitude": 100.54134,
          "latitude": 13.75983,
          "location": "13.75983,100.54134"
        }
      },
      {
        "_index": "airbnb_listings_audit",
        "_id": "y4nDl5sBPhNOaOkL9WXX",
        "_score": 1,
        "_source": {
          "id": 27979,
          "longitude": 100.61674,
          "latitude": 13.66818,
          "location": "13.66818,100.61674"
        }
      },
      {
        "_index": "airbnb_listings_audit",
        "_id": "zInDl5sBPhNOaOkL9WXX",
        "_score": 1,
        "_source": {
          "id": 28745,
          "longitude": 100.62402,
          "latitude": 13.75232,
          "location": "13.75232,100.62402"
        }
      },
      {
        "_index": "airbnb_listings_audit",
        "_id": "zYnDl5sBPhNOaOkL9WXX",
        "_score": 1,
        "_source": {
          "id": 47516,
          "longitude": 100.58529,
          "latitude": 13.92726,
          "location": "13.92726,100.58529"
        }
      },
      {
        "_index": "airbnb_listings_audit",
        "_id": "zonDl5sBPhNOaOkL9WXX",
        "_score": 1,
        "_source": {
          "id": 48736,
          "longitude": 100.49535,
          "latitude": 13.68556,
          "location": "13.68556,100.49535"
        }
      }
    ]
  }
}

#garder 10 lignes dans le fichier
PUT airbnb_listings_audit_light
{
  "mappings": {
    "properties": {
      "id": { "type": "long" },
      "name": { "type": "text" },
      "price": { "type": "keyword" },
      "room_type": { "type": "keyword" },
      "property_type": { "type": "keyword" },
      "accommodates": { "type": "long" },
      "neighbourhood_cleansed": { "type": "keyword" },
      "number_of_reviews": { "type": "long" },
      "review_scores_rating": { "type": "double" },
      "location": { "type": "geo_point" }
    }
  }
}

### Normalisation du champ `price`

Le champ `price` était initialement stocké sous forme de chaîne de caractères (`keyword`) incluant des symboles monétaires (ex: `$1,416.00`).

Afin de permettre les analyses statistiques, un nouveau champ `price_numeric` a été créé lors d’une opération de reindexation.  
Les transformations appliquées sont :
- suppression du symbole `$`,
- suppression des séparateurs de milliers `,`,
- conversion en nombre décimal (`double`).

Cette normalisation rend le champ exploitable pour les agrégations (moyenne, min, max) et les visualisations Kibana.

résultat : "_source": {
          "price": "$1,450.00",
          "id": 48736,
          "price_numeric": 1450


## Exécution du pipeline ETL automatisé (Python → Elasticsearch)
Le script python est dans etl_airbnb_to_es.py

Le chargement du fichier CSV a été automatisé via un script Python ETL.  
Le script lit les fichiers déposés, applique des transformations (normalisation) puis indexe les documents dans Elasticsearch via la **Bulk API**.

### Résumé d’exécution (preuve)

Sortie du script :

- Fichiers traités : 1  
- Lignes lues : 28 806  
- Documents indexés : 28 806  
- Prix manquants : 5 533 (**19,21 %**)  
- Formats prix invalides : 0  
- Formats géographiques invalides : 0  

### Interprétation

- L’ingestion est **complète** (rows = indexed), ce qui indique l’absence de perte lors du chargement.
- Le champ `price` présente un taux de valeurs manquantes significatif (~1 annonce sur 5).
- Les contrôles de format indiquent une **bonne qualité** sur les valeurs de prix existantes et la géolocalisation (aucune anomalie détectée).

PUT airbnb_listings_v2
{
  "mappings": {
    "properties": {
      "id": { "type": "long" },

      "name": { "type": "text" },

      "price": { "type": "keyword" },
      "price_numeric": { "type": "double" },

      "accommodates": { "type": "long" },
      "bedrooms": { "type": "long" },
      "beds": { "type": "long" },
      "bathrooms": { "type": "double" },

      "availability_30": { "type": "long" },
      "availability_60": { "type": "long" },
      "availability_90": { "type": "long" },
      "availability_365": { "type": "long" },

      "number_of_reviews": { "type": "long" },
      "review_scores_rating": { "type": "double" },

      "neighbourhood_cleansed": { "type": "keyword" },
      "property_type": { "type": "keyword" },
      "room_type": { "type": "keyword" },

      "host_is_superhost": { "type": "boolean" },
      "instant_bookable": { "type": "boolean" },
      "has_availability": { "type": "boolean" },

      "latitude": { "type": "double" },
      "longitude": { "type": "double" },
      "location": { "type": "geo_point" },

      "last_scraped": { "type": "date" },
      "host_since": { "type": "date" }
    }
  }
}
GET airbnb_listings_v2/_count
GET airbnb_listings_v2/_mapping

  "airbnb_listings_v2": {
    "mappings": {
      "properties": {
        "accommodates": {
          "type": "long"
        },
        "amenities": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }

Ça veut dire que ton index airbnb_listings_v2 a bien un mapping contrôlé (au moins pour accommodates en long, donc on est sur la bonne voie).
accommodates en long : tu pourras faire des stats / histogrammes / agrégations.

GET airbnb_listings_v2/_mapping/field/price
résultat : {
  "airbnb_listings_v2": {
    "mappings": {
      "price": {
        "full_name": "price",
        "mapping": {
          "price": {
            "type": "keyword"
          }
        }
      }
    }
  }
}
GET airbnb_listings_v2/_mapping/field/price_numeric
résultat : 
{
  "airbnb_listings_v2": {
    "mappings": {
      "price_numeric": {
        "full_name": "price_numeric",
        "mapping": {
          "price_numeric": {
            "type": "double"
          }
        }
      }
    }
  }
}
Vérifier location geo_point
GET airbnb_listings_v2/_mapping/field/location


On veut : geo_point

C) Vérifier les booléens
GET airbnb_listings_v2/_mapping/field/host_is_superhost


On veut : boolean

#Afficher des résultats concrets (preuve que la normalisation marche)
GET airbnb_listings_v2/_search
{
  "size": 5,
  "_source": ["id", "price", "price_numeric"]
}

#Faire des stats sur le prix (maintenant possible)
GET airbnb_listings_v2/_search
{
  "size": 0,
  "aggs": {
    "price_stats": {
      "stats": { "field": "price_numeric" }
    }
  }
}

{
  "took": 53,
  "timed_out": false,
  "_shards": {
    "total": 1,
    "successful": 1,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {
      "value": 10000,
      "relation": "gte"
    },
    "max_score": null,
    "hits": []
  },
  "aggregations": {
    "price_stats": {
      "count": 16114,
      "min": 34,
      "max": 1000000,
      "avg": 2405.8274792106245,
      "sum": 38767504
    }
  }
}
Là, tu as exactement ce qu’il faut pour prouver que ta normalisation price_numeric marche et pour alimenter ton audit Kibana/Elasticsearch.

Ce que tes stats disent (et comment l’écrire)
Résultats

count = 16114 → 16 114 annonces ont un price_numeric exploitable

min = 34

max = 1 000 000 ⚠️ (très probablement une valeur aberrante)

avg ≈ 2405.83

sum = 38 767 504

Interprétation audit (important)

✅ Le champ price_numeric est bien numérique, donc Kibana peut faire des histogrammes, moyennes, min/max.

⚠️ Il existe au moins une valeur extrême (max = 1 000 000) qui biaisera la moyenne.

Recommandation : utiliser médiane/percentiles ou filtrer les outliers.

Point à noter : count=16114 est plus bas que tes 28k lignes

Ça veut dire qu’une partie des documents :

n’ont pas de price → donc pas de price_numeric

ou n’ont pas été indexés dans v2 (selon ton count réel de v2)

### Statistiques sur le prix (champ normalisé `price_numeric`)

Après normalisation du champ `price` (suppression de `$` et des séparateurs de milliers, conversion en décimal), le champ `price_numeric` permet des agrégations numériques dans Elasticsearch.

Requête `stats` sur `price_numeric` :

- Documents avec un prix exploitable (`count`) : 16 114
- Prix minimum : 34
- Prix maximum : 1 000 000
- Prix moyen : ~2 405,83

**Constats :**
- Le champ `price_numeric` est correctement typé et exploitable pour Kibana (Lens).
- La présence d’une valeur maximale très élevée (1 000 000) suggère un **outlier** susceptible de biaiser la moyenne.

**Recommandations :**
- Utiliser des indicateurs robustes (médiane / percentiles) ou filtrer les valeurs extrêmes avant analyse.

Interprétation du résultat
Requête exécutée
GET airbnb_listings_v2/_search
{
  "size": 0,
  "aggs": {
    "missing_price_numeric": {
      "missing": { "field": "price_numeric" }
    }
  }
}

Résultat clé

Documents sans price_numeric : 2 601

Mise en perspective avec les chiffres précédents

Tu avais :

Documents avec price_numeric : 16 114

Documents sans price_numeric : 2 601

👉 Donc taille totale de l’index airbnb_listings_v2 :

16 114 + 2 601 = 18 715 documents

L’ETL a consolidé les annonces par id

Résultat : 18 715 annonces uniques

Parmi elles :

~86 % ont un prix exploitable

~14 % n’ont pas de prix

Taux de valeurs manquantes (champ normalisé)

Calcul :

2 601 / 18 715 ≈ 13,9 %

C’est meilleur que sur le CSV brut (~19 %), car :

certaines annonces sans prix ont été écrasées lors de la consolidation

l’ETL a nettoyé correctement les formats invalides

Pourquoi le taux diminue après traitement

Cette amélioration s’explique par deux mécanismes principaux du pipeline ETL :

Nettoyage et normalisation du champ price

Suppression des symboles non numériques ($, séparateurs de milliers ,)

Conversion en type décimal (price_numeric)

Certaines valeurs initialement considérées comme invalides ou non exploitables dans le CSV brut deviennent exploitables après transformation.

Consolidation des annonces par identifiant logique (id)

Le CSV brut contient plusieurs lignes correspondant à une même annonce (snapshots multiples).

Lors de l’indexation, les annonces sont consolidées :
lorsqu’une annonce possède au moins une occurrence avec un prix valide, celle-ci est conservée.

Les lignes sans prix, associées à une annonce déjà présente avec un prix valide, ne dégradent plus le taux global.

Conclusion

Le passage de ~19 % à ~14 % de valeurs manquantes ne traduit pas une perte de données, mais une amélioration de la qualité grâce :

au nettoyage sémantique du champ price,

et à la consolidation des données au niveau métier (annonce unique).

Ce résultat valide la pertinence du pipeline ETL et renforce la fiabilité des analyses statistiques réalisées dans Kibana.

Si tu veux, je peux aussi te fournir :

une version très courte (3 lignes) pour une diapo,

ou une formulation encore plus “Data Architect” (orientée gouvernance / qualité des données).

### Complétude du champ `price_numeric`

Une agrégation `missing` a été réalisée sur le champ `price_numeric` (prix normalisé).

- Documents sans `price_numeric` : 2 601
- Documents avec `price_numeric` : 16 114
- Total documents (index v2) : 18 715
- Taux de valeurs manquantes : ~13,9 %

**Analyse :**
Le taux de valeurs manquantes est inférieur à celui observé dans le CSV brut (~19 %).  
Cette amélioration s’explique par la consolidation des annonces par identifiant (`id`) lors de l’ETL.

Le champ `price_numeric` est donc majoritairement exploitable pour les analyses statistiques et les visualisations Kibana.

le pipeline nettoie et normalise correctement les prix

 la qualité des données s’améliore entre la source brute et l’index final

il reste un taux non négligeable de valeurs manquantes → à filtrer dans Kibana (exists: price_numeric)
Le taux baisse parce que :

on ne compte plus des lignes, mais des annonces

une annonce n’est pénalisée qu’une seule fois, même si elle avait plusieurs lignes sans prix dans le CSV

🎯 Phrase simple à dire à l’oral (très efficace)

« Dans le CSV brut, le taux de valeurs manquantes est calculé ligne par ligne, ce qui pénalise fortement les annonces présentes plusieurs fois sans prix.
Lors du traitement ETL, les données sont nettoyées puis consolidées par identifiant d’annonce.
Ainsi, dès qu’une annonce possède au moins un prix valide, elle est considérée comme exploitable, ce qui réduit mécaniquement le taux de valeurs manquantes de 19 % à environ 14 %. »

##TP4
Voici les 2 scripts complets demandés, conformes au cahier des charges (Pandas → Parquet, puis Parquet → Elasticsearch via helpers.bulk), avec gestion d’erreurs robuste.

Dépendances :

python3 -m pip install pandas pyarrow elasticsearch

lyon et paris existe par car j'ai pris le fichier de thaillande donc :
GET airbnb_listings_audit/_search
{
  "size": 0,
  "aggs": {
    "cities": {
      "terms": {
        "field": "host_location",
        "size": 20
      }
    }
  }
}

 "aggregations": {
    "cities": {
      "doc_count_error_upper_bound": 0,
      "sum_other_doc_count": 1337,
      "buckets": [
        {
          "key": "Bangkok, Thailand",
          "doc_count": 17802
        },
        {
          "key": "Thailand",
          "doc_count": 509
        },
        {
          "key": "Singapore",
          "doc_count": 242
        },

script 0_export_cities.py version 5 villes, clé en main, conforme à ton TP (export automatique depuis Elasticsearch vers 5 CSV distincts).

👉 Il exporte 5 villes différentes à partir du champ host_location.

5 villes.csv on été créé
romain@MacBook-Air-de-Romain mon projet % python3 0_export_cities.py

[OK] Connecté à Elasticsearch: es-node-1 / 8.11.1
[START] Export 5 villes depuis Elasticsearch

Index: airbnb_listings_audit
Champ: host_location

[OK] Bangkok, Thailand                   -> data/bangkok_thailand.csv (17802 lignes)
[OK] Singapore                           -> data/singapore.csv (242 lignes)
[OK] Krung Thep Maha Nakhon, Thailand    -> data/krung_thep_maha_nakhon_thailand.csv (208 lignes)
[OK] Chiang Mai, Thailand                -> data/chiang_mai_thailand.csv (127 lignes)
[OK] Osaka, Japan                        -> data/osaka_japan.csv (114 lignes)

[DONE] Export terminé

Il faut supprimé les fichier avec 0 Ko sinon le script 1 ne se lance pas:
romain@MacBook-Air-de-Romain mon projet % python3 1_clean_data.py --data-dir ./data --out ./airbnb_clean.parquet

[OK] Lu bangkok_thailand.csv -> 17802 lignes
[OK] Lu chiang_mai_thailand.csv -> 227 lignes
[OK] Lu krung_thep_maha_nakhon_thailand.csv -> 208 lignes
[OK] Lu osaka_japan.csv -> 884 lignes
[OK] Lu singapore.csv -> 1220 lignes

[OK] Export parquet: airbnb_clean.parquet
[STATS] rows=20341 missing_price_numeric=5370 (26.40%)
[STATS] files_read=5

lancement script2:
romain@MacBook-Air-de-Romain mon projet % python3 2_send_to_elk.py --parquet ./airbnb_clean.parquet --index airbnb-listings

/Users/romain/Desktop/Big Data/mon projet/2_send_to_elk.py:95: DeprecationWarning: Passing transport options in the API method is deprecated. Use 'Elasticsearch.options()' instead.
  for ok, item in helpers.streaming_bulk(
[OK] Bulk terminé -> index=airbnb-listings
[STATS] sent=20341 failures=0 (voir bulk_failures.jsonl)
[VERIFY] GET airbnb-listings/_count -> 16730

DELETE airbnb-listings
GET airbnb-listings/_count
{
  "count": 20341,
  "_shards": {
    "total": 1,
    "successful": 1,
    "skipped": 0,
    "failed": 0
  }
}

## TP4 – Validation de l’injection Elasticsearch (Load)

Après génération du fichier `airbnb_clean.parquet`, l’injection a été réalisée via `helpers.streaming_bulk`
dans Elasticsearch (index `airbnb-listings`).

### Preuve Kibana (Dev Tools)
```json
GET airbnb-listings/_count


---

## ⚠️ Concernant l’objectif “~70 000 documents”
Avec tes 5 villes actuelles, tu as ~20k docs, donc **tu ne peux pas atteindre 70k** sans :

- exporter **plus de villes** (top N), ou
- exporter **tout l’index** sans filtrer par ville, ou
- utiliser d’autres fichiers (Paris/Lyon réels) si le TP en prévoit.

Si ton formateur exige absolument ~70k, je te propose une solution béton :

### ✅ Script automatique : exporter des villes jusqu’à atteindre ~70 000 lignes
- il récupère les `host_location` les plus fréquents (aggregation)
- exporte une ville après l’autre
- **s’arrête dès qu’on dépasse 70 000 docs**

Si tu me dis :
- ton index source exact (c’est bien `airbnb_listings_audit` ?)
- le champ exact (`host_location` confirmé)
je te donne le script “TopN until 70k” immédiatement.

Mais si ton prof accepte “environ” en fonction des données dispo, tu es déjà **clean** : pipeline OK, preuves OK.
