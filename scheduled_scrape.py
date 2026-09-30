#!/usr/bin/env python3
"""Scheduled scraper: run sentiment analysis on a schedule and save results.

Usage:
    python3 scheduled_scrape.py --keyword "taspen" --max 60

Results saved to hasil/ with timestamp. For trend tracking, run via cron:
    0 */6 * * * cd /root/ig-sentiment && ./venv/bin/python3 scheduled_scrape.py --keyword "taspen" --max 60 >> /var/log/sentiment_cron.log 2>&1
"""
import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config import OUT_DIR, MODEL_NAME
from multiscrape import dedupe, scrape_ig, scrape_web, scrape_yt
from scrapers_extra import scrape_playstore
from taspen_categorize import classify_df
from transformers import pipeline as hf_pipeline

LABEL_ID = {"positive": "Positif", "neutral": "Netral", "negative": "Negatif"}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_sentiment_batch(df):
    """Run sentiment model on dataframe."""
    clf = hf_pipeline("text-classification", model=MODEL_NAME,
                      truncation=True, max_length=128, device=-1)
    texts = df["text"].astype(str).tolist()
    labels, scores = [], []
    B = 16
    for i in range(0, len(texts), B):
        batch = texts[i:i + B]
        res = clf(batch)
        labels += [r["label"] for r in res]
        scores += [round(r["score"], 4) for r in res]
        if (i + B) % 64 == 0:
            log(f"  sentiment {min(i+B, len(texts))}/{len(texts)}")
    df["label"] = [LABEL_ID.get(str(l).lower(), l) for l in labels]
    df["score"] = scores
    df["keyakinan"] = ["yakin" if s >= 0.6 else "ragu" for s in scores]
    df = classify_df(df)
    return df


def main():
    parser = argparse.ArgumentParser(description="Scheduled sentiment scrape")
    parser.add_argument("--keyword", required=True, help="Search keyword")
    parser.add_argument("--max", type=int, default=60, help="Max comments per source")
    parser.add_argument("--yt", type=int, default=60, help="Max YT comments")
    parser.add_argument("--web", type=int, default=8, help="Max web articles")
    parser.add_argument("--ps", type=int, default=60, help="Max Play Store reviews")
    parser.add_argument("--sources", default="yt,web,ps", help="Comma-separated: yt,web,ps,ig,fb,tt")
    args = parser.parse_args()

    sources = args.sources.split(",")
    t0 = time.time()
    rows = []

    def ambil(nama, fn, n):
        if n <= 0 or nama.lower() not in [s.strip() for s in sources]:
            return
        log(f"▶ {nama}: mulai (target {n})...")
        try:
            got = fn(args.keyword.strip(), n, log)
            rows.extend(got)
            log(f"✓ {nama}: {len(got)} baris")
        except Exception as e:
            log(f"✗ {nama}: {type(e).__name__} {str(e)[:120]}")

    ambil("yt", scrape_yt, args.yt)
    ambil("web", scrape_web, args.web)
    ambil("ps", scrape_playstore, args.ps)
    if "ig" in sources:
        ambil("ig", scrape_ig, args.max)
    if "fb" in sources:
        from scrapers_extra import scrape_facebook
        ambil("fb", scrape_facebook, args.max)
    if "tt" in sources:
        from scrapers_extra import scrape_tiktok
        ambil("tt", scrape_tiktok, args.max)

    rows = dedupe(rows)
    if not rows:
        log("Tidak ada data. Exit.")
        return

    log(f"Total raw: {len(rows)} rows. Running sentiment...")
    df = pd.DataFrame(rows)
    df = run_sentiment_batch(df)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_csv = OUT_DIR / f"scheduled_{args.keyword.strip().replace(' ', '_')}_{stamp}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")

    # Summary
    total = len(df)
    cnt = df["label"].value_counts()
    gss = round((cnt.get("Positif", 0) + 0.5 * cnt.get("Netral", 0)) / total * 100, 1)
    skor = round(100 * cnt.get("Positif", 0) / total - 100 * cnt.get("Negatif", 0) / total, 1)

    log(f"✅ Done: {total} rows, P={cnt.get('Positif',0)} N={cnt.get('Netral',0)} Neg={cnt.get('Negatif',0)}")
    log(f"   GSS={gss}/100, Skor={skor:+.1f}")
    log(f"   Saved: {out_csv}")
    log(f"   Duration: {round(time.time()-t0)}s")


if __name__ == "__main__":
    main()
