#!/usr/bin/env bash
# Full pipeline KEYWORD: hashtag -> scrape postingan+komentar -> sentiment
#   -> summary + CSV ke LINE
# Pakai: ./run_keyword_pipeline.sh "KEYWORD" [POSTS] [PER_POST]
set -euo pipefail
cd /root/ig-sentiment

KEYWORD="${1:?Keyword wajib, contoh: kuliner}"
POSTS="${2:-5}"
PER_POST="${3:-30}"
TO="Ub74d3487b50860ee199e86c67b8ee99b"
TS=$(date +%Y%m%d-%H%M%S)
CSV="hasil/komentar-${TS}.csv"
LAB="hasil/berlabel-${TS}.csv"
mkdir -p hasil

echo "[1/4] scrape komentar keyword '${KEYWORD}' ..."
IG_PROXY=socks5://127.0.0.1:40000 ./venv/bin/python keyword_scrape.py \
  --keyword "$KEYWORD" --posts "$POSTS" --per-post "$PER_POST" --out "$CSV"

echo "[2/4] sentiment analysis ..."
HF_HOME=/root/ig-sentiment/hf ./venv/bin/python sentiment.py \
  --in "$CSV" --out "$LAB"

echo "[3/4] buat ringkasan ..."
SUM=$(./venv/bin/python summarize.py "$LAB" "Keyword: #${KEYWORD}")

echo "[4/4] kirim ke LINE ..."
./venv/bin/python line_send.py --to "$TO" --file "$LAB" --text "$SUM"

echo "[✓] selesai: $LAB"
