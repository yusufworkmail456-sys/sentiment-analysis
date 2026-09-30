#!/usr/bin/env python3
"""Sentiment analysis komentar dari CSV scrape.py -> CSV berlabel.

Pakai:
  ./venv/bin/python sentiment.py --in komentar.csv --out berlabel.csv
Model: w11wo/indonesian-roberta-base-sentiment-classifier (positif/netral/negatif)
"""
import argparse
import csv
import sys

import pandas as pd
from transformers import pipeline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="CSV dari scrape.py")
    ap.add_argument("--out", default="berlabel.csv", help="CSV output berlabel")
    ap.add_argument("--batch", type=int, default=16)
    args = ap.parse_args()

    df = pd.read_csv(args.inp).dropna(subset=["text"]).reset_index(drop=True)
    if df.empty:
        print("[!] CSV kosong", file=sys.stderr)
        return 1

    print(f"[i] load model (pertama kali download ~500MB) ...", file=sys.stderr)
    clf = pipeline(
        "text-classification",
        model="w11wo/indonesian-roberta-base-sentiment-classifier",
        truncation=True,
        max_length=128,
        device=-1,  # CPU
    )

    texts = df["text"].astype(str).tolist()
    print(f"[i] analisis {len(texts)} komentar ...", file=sys.stderr)
    results = []
    for i in range(0, len(texts), args.batch):
        batch = texts[i : i + args.batch]
        results.extend(clf(batch))
        done = min(i + args.batch, len(texts))
        if done % 100 < args.batch:
            print(f"[i] {done}/{len(texts)}", file=sys.stderr)

    df["label"] = [r["label"] for r in results]
    df["score"] = [round(r["score"], 4) for r in results]
    df.to_csv(args.out, index=False, encoding="utf-8")

    dist = df["label"].value_counts()
    total = len(df)
    print("\n=== Ringkasan Sentimen ===", file=sys.stderr)
    for label, n in dist.items():
        print(f"  {label:10s} {n:6d}  ({n/total*100:.1f}%)", file=sys.stderr)
    print(f"[✓] tersimpan -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
