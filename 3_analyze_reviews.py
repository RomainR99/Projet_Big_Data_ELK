#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TP NLP - Etape 1
Script: 3_analyze_reviews.py

- Lecture CSV par chunks (gros volume)
- Nettoyage basique (lignes vides)
- Sentiment (TextBlob polarity -1 à +1)
- Label: Negatif / Neutre / Positif
- Ajout target_city (bangkok / barcelona)
- Indexation Bulk vers airbnb-reviews

Usage:
python3 3_analyze_reviews.py \
  --bangkok ./reviews_bankok.csv \
  --barcelona ./reviews_barcelona.csv \
  --es http://localhost:9200 \
  --index airbnb-reviews \
  --chunk-size 5000 \
  --bulk-chunk 2000
"""

from __future__ import annotations

from tqdm import tqdm
import argparse
import json
from pathlib import Path
from typing import Dict, Iterator, Optional

import pandas as pd
from elasticsearch import Elasticsearch, helpers
from pandas.errors import EmptyDataError
from textblob import TextBlob


def ensure_index(es: Elasticsearch, index_name: str) -> None:
    if es.indices.exists(index=index_name):
        return

    body = {
        "mappings": {
            "properties": {
                "review_id": {"type": "keyword"},
                "listing_id": {"type": "keyword"},
                "date": {"type": "date", "ignore_malformed": True},
                "reviewer_id": {"type": "keyword"},
                "reviewer_name": {"type": "keyword"},
                "comments": {"type": "text"},
                "sentiment_polarity": {"type": "float"},
                "sentiment_label": {"type": "keyword"},
                "target_city": {"type": "keyword"},
            }
        }
    }
    es.indices.create(index=index_name, body=body)


def detect_delimiter(sample_path: Path) -> str:
    with sample_path.open("r", encoding="utf-8", errors="replace") as f:
        head = f.readline()
    return "\t" if head.count("\t") > head.count(",") else ","


def read_csv_chunks(path: Path, chunksize: int) -> Iterator[pd.DataFrame]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    if path.stat().st_size == 0:
        raise EmptyDataError(f"Fichier vide: {path}")

    sep = detect_delimiter(path)
    
    return pd.read_csv(
    path,
    sep=sep,
    chunksize=chunksize,
    low_memory=False,
    encoding="utf-8",
    )



def polarity_and_label(text: str) -> tuple[float, str]:
    pol = float(TextBlob(text).sentiment.polarity)
    if pol < 0:
        return pol, "Negatif"
    if pol > 0:
        return pol, "Positif"
    return pol, "Neutre"


def pick_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def iter_actions(chunk: pd.DataFrame, index_name: str, city_label: str, text_col: str) -> Iterator[Dict]:
    id_col = pick_col(chunk, ["id", "review_id"])
    listing_col = pick_col(chunk, ["listing_id"])
    date_col = pick_col(chunk, ["date"])
    reviewer_id_col = pick_col(chunk, ["reviewer_id"])
    reviewer_name_col = pick_col(chunk, ["reviewer_name"])

    for _, row in chunk.iterrows():
        txt = row.get(text_col, None)
        if txt is None:
            continue

        comments = str(txt).strip()
        if not comments:
            continue

        pol, lab = polarity_and_label(comments)

        doc = {
            "comments": comments,
            "sentiment_polarity": pol,
            "sentiment_label": lab,
            "target_city": city_label,
        }

        if id_col and pd.notna(row.get(id_col)):
            doc["review_id"] = str(row.get(id_col))
        if listing_col and pd.notna(row.get(listing_col)):
            doc["listing_id"] = str(row.get(listing_col))
        if date_col and pd.notna(row.get(date_col)):
            doc["date"] = row.get(date_col)
        if reviewer_id_col and pd.notna(row.get(reviewer_id_col)):
            doc["reviewer_id"] = str(row.get(reviewer_id_col))
        if reviewer_name_col and pd.notna(row.get(reviewer_name_col)):
            doc["reviewer_name"] = str(row.get(reviewer_name_col))

        yield {"_op_type": "index", "_index": index_name, "_source": doc}


def process_file(es: Elasticsearch, index_name: str, path: Path, city_label: str,
                 chunk_size: int, bulk_chunk: int, fail_log_fh, text_col: str) -> tuple[int, int, int]:
    sent = 0
    failures = 0
    skipped_empty = 0

    for i, chunk in enumerate(read_csv_chunks(path, chunk_size), start=1):
        print(f"\n[CHUNK] {city_label} -> chunk {i} (rows brutes={len(chunk)})")

        if text_col not in chunk.columns:
            raise ValueError(f"Colonne '{text_col}' introuvable dans {path.name}. Colonnes: {list(chunk.columns)}")

        before = len(chunk)
        chunk = chunk[chunk[text_col].notna()]
        chunk[text_col] = chunk[text_col].astype("string").str.strip()
        chunk = chunk[chunk[text_col] != ""]
        skipped_empty += (before - len(chunk))

        actions = iter_actions(chunk, index_name, city_label, text_col)

        pbar = tqdm(
            total=len(chunk),
            desc=f"Index {city_label} (chunk {i})",
            unit="doc",
            leave=False
        )

        for ok, item in helpers.streaming_bulk(
            client=es,
            actions=actions,
            chunk_size=bulk_chunk,
            raise_on_error=False,
            raise_on_exception=False,
            request_timeout=120,
        ):
            sent += 1
            pbar.update(1)

            if not ok:
                failures += 1
                fail_log_fh.write(json.dumps(item, ensure_ascii=False) + "\n")

        pbar.close()


        print(f"[INFO] {city_label} chunk {i}: processed_rows={len(chunk)} total_indexed={sent} failures={failures}")

    return sent, failures, skipped_empty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bangkok", required=True, help="Chemin vers reviews_bangkok.csv (chez toi: reviews_bankok.csv)")
    ap.add_argument("--barcelona", required=True, help="Chemin vers reviews_barcelona.csv")
    ap.add_argument("--es", default="http://localhost:9200")
    ap.add_argument("--index", default="airbnb-reviews")
    ap.add_argument("--chunk-size", type=int, default=5000)
    ap.add_argument("--bulk-chunk", type=int, default=2000)
    ap.add_argument("--fail-log", default="reviews_bulk_failures.jsonl")
    ap.add_argument("--text-col", default="comments")
    args = ap.parse_args()

    es = Elasticsearch(args.es)
    info = es.info()
    print(f"[OK] Connecté à Elasticsearch: {info['name']} / {info['version']['number']}")

    ensure_index(es, args.index)

    total_sent = 0
    total_failures = 0
    total_skipped = 0

    with open(args.fail_log, "w", encoding="utf-8") as f_log:
        sent, failures, skipped = process_file(
            es, args.index, Path(args.bangkok), "bangkok",
            args.chunk_size, args.bulk_chunk, f_log, args.text_col
        )
        total_sent += sent
        total_failures += failures
        total_skipped += skipped

        sent, failures, skipped = process_file(
            es, args.index, Path(args.barcelona), "barcelona",
            args.chunk_size, args.bulk_chunk, f_log, args.text_col
        )
        total_sent += sent
        total_failures += failures
        total_skipped += skipped

    print("\n[OK] NLP + Bulk terminé")
    print(f"[STATS] indexed={total_sent} failures={total_failures} empty_or_blank_rows_skipped={total_skipped}")
    print(f"[VERIFY] GET {args.index}/_count -> {es.count(index=args.index)['count']}")
    print(f"[LOG] failures -> {args.fail_log}")


if __name__ == "__main__":
    main()

