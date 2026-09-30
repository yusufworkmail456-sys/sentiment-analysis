#!/usr/bin/env bash
# Full pipeline: URL IG -> scrape -> sentiment -> summary + CSV ke LINE
# Pakai: ./run_pipeline.sh "URL_POSTINGAN" [LIMIT]
set -euo pipefail
cd /root/ig-sentiment

URL="${1:?URL postingan wajib}"
LIMIT="${2:-200}"
TO="Ub74d3487b50860ee199e86c67b8ee99b"
TS=$(date +%Y%m%d-%H%M%S)
CSV="hasil/komentar-${TS}.csv"
LAB="hasil/berlabel-${TS}.csv"
mkdir -p hasil

echo "[1/4] scrape komentar ..."
IG_PROXY=socks5://127.0.0.1:40000 ./venv/bin/python scrape.py \
  --url "$URL" --out "$CSV" --limit "$LIMIT"

echo "[2/4] sentiment analysis ..."
HF_HOME=/root/ig-sentiment/hf ./venv/bin/python sentiment.py \
  --in "$CSV" --out "$LAB"

echo "[3/4] buat ringkasan ..."
SUM=$(./venv/bin/python summarize.py "$LAB" "$URL")

echo "[4/4] kirim ke LINE ..."
./venv/bin/python line_send.py --to "$TO" --file "$LAB" --text "$SUM"

echo "[✓] selesai: $LAB"
