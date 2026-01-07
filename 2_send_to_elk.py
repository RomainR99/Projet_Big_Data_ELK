#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterator

import pandas as pd
from elasticsearch import Elasticsearch, helpers


def iter_actions(df: pd.DataFrame, index_name: str) -> Iterator[Dict]:
    for _, row in df.iterrows():
        doc = row.to_dict()
        # NaN -> None
        for k, v in list(doc.items()):
            if pd.isna(v):
                doc[k] = None

        # IMPORTANT: on ne fixe pas _id (pour éviter d’écraser)
        yield {
            "_op_type": "index",
            "_index": index_name,
            "_source": doc,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", default="./airbnb_clean.parquet")
    ap.add_argument("--es", default="http://localhost:9200")
    ap.add_argument("--index", default="airbnb-listings")
    ap.add_argument("--chunk-size", type=int, default=2000)
    ap.add_argument("--fail-log", default="bulk_failures.jsonl")
    args = ap.parse_args()

    parquet_path = Path(args.parquet)
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet introuvable: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    es = Elasticsearch(args.es)
    info = es.info()
    print(f"[OK] Connecté à Elasticsearch: {info['name']} / {info['version']['number']}")

    sent = 0
    failures = 0

    with open(args.fail_log, "w", encoding="utf-8") as f_log:
        for ok, item in helpers.streaming_bulk(
            client=es,
            actions=iter_actions(df, args.index),
            chunk_size=args.chunk_size,
            raise_on_error=False,
            raise_on_exception=False,
            request_timeout=120,
        ):
            sent += 1
            if not ok:
                failures += 1
                f_log.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[OK] Bulk terminé -> index={args.index}")
    print(f"[STATS] sent={sent} failures={failures} (voir {args.fail_log})")
    print(f"[VERIFY] GET {args.index}/_count -> {es.count(index=args.index)['count']}")


if __name__ == "__main__":
    main()



