#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

PRICE_CLEAN_RE = re.compile(r"[^\d\.\-]")  # garde chiffres, point, signe -

KEEP_COLS = [
    "id", "name",
    "host_id", "host_is_superhost",
    "neighbourhood_cleansed", "room_type", "target_city",
    "price", "review_scores_rating",
    "accommodates", "bedrooms", "beds",
    "number_of_reviews", "minimum_nights",
    "latitude", "longitude",
    "location",
]


def read_csv_flexible(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable: {path}")
    if path.stat().st_size == 0:
        raise EmptyDataError(f"Fichier vide: {path}")

    # Airbnb est parfois TSV
    try:
        return pd.read_csv(path, sep="\t", compression="infer", low_memory=False)
    except Exception:
        return pd.read_csv(path, sep=",", compression="infer", low_memory=False)


def clean_price_to_float(s: pd.Series) -> pd.Series:
    s = s.astype("string")
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(PRICE_CLEAN_RE, "", regex=True)
    return pd.to_numeric(s, errors="coerce").astype("float64")


def to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")


def build_location(lat: pd.Series, lon: pd.Series) -> pd.Series:
    lat_num = pd.to_numeric(lat, errors="coerce")
    lon_num = pd.to_numeric(lon, errors="coerce")
    loc = lat_num.astype("string") + "," + lon_num.astype("string")
    return loc.mask(lat_num.isna() | lon_num.isna(), pd.NA)


def normalize(df: pd.DataFrame, city_label: str) -> pd.DataFrame:
    df = df.copy()
    df["target_city"] = city_label

    # id / host_id -> string (keyword ES)
    if "id" in df.columns:
        df["id"] = df["id"].astype("string")
    else:
        df["id"] = pd.NA

    if "host_id" in df.columns:
        df["host_id"] = df["host_id"].astype("string")
    else:
        df["host_id"] = pd.NA

    # price -> float
    if "price" in df.columns:
        df["price"] = clean_price_to_float(df["price"])
    else:
        df["price"] = pd.NA

    # numeric fields -> Int64
    for col in ["accommodates", "bedrooms", "beds", "number_of_reviews", "minimum_nights"]:
        if col in df.columns:
            df[col] = to_int(df[col])
        else:
            df[col] = pd.NA

    # review_scores_rating -> float
    if "review_scores_rating" in df.columns:
        df["review_scores_rating"] = pd.to_numeric(df["review_scores_rating"], errors="coerce").astype("float64")
    else:
        df["review_scores_rating"] = pd.NA

    # location geo_point "lat,lon"
    if "latitude" in df.columns and "longitude" in df.columns:
        df["location"] = build_location(df["latitude"], df["longitude"])
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").astype("float64")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").astype("float64")
    else:
        df["location"] = pd.NA
        df["latitude"] = pd.NA
        df["longitude"] = pd.NA

    # garder seulement les colonnes utiles (mapping)
    for c in KEEP_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[KEEP_COLS]

    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bangkok", required=True, help="Chemin vers listings_bangkok.csv")
    ap.add_argument("--barcelona", required=True, help="Chemin vers listings_barcelona.csv")
    ap.add_argument("--out", default="airbnb_clean.parquet", help="Fichier parquet de sortie")
    args = ap.parse_args()

    df_bkk = read_csv_flexible(Path(args.bangkok))
    df_bcn = read_csv_flexible(Path(args.barcelona))

    df_bkk = normalize(df_bkk, "bangkok")
    df_bcn = normalize(df_bcn, "barcelona")

    df_all = pd.concat([df_bkk, df_bcn], ignore_index=True)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_parquet(out_path, index=False)

    total = len(df_all)
    missing_price = int(df_all["price"].isna().sum())
    missing_loc = int(df_all["location"].isna().sum())

    print(f"[OK] Export parquet: {out_path}")
    print(f"[STATS] rows={total}")
    print(f"[STATS] missing_price={missing_price} ({(missing_price/total*100 if total else 0):.2f}%)")
    print(f"[STATS] missing_location={missing_loc} ({(missing_loc/total*100 if total else 0):.2f}%)")


if __name__ == "__main__":
    main()



