# Scraper Komentar Instagram + Sentiment Analysis

Pipeline: URL postingan IG -> CSV komentar -> CSV berlabel sentimen (positif/netral/negatif).

Semua jalan di VPS (`/root/ig-sentiment/`). Traffic IG lewat Cloudflare WARP
(proxy SOCKS5 lokal 127.0.0.1:40000) supaya tidak kena blok IP datacenter.

## Cek WARP (sekali sesekali)

```
warp-cli status          # harus: Connected, mode proxy
curl -s --socks5-hostname 127.0.0.1:40000 ifconfig.me   # IP Cloudflare, bukan 69.5.22.24
```

Kalau disconnected: `warp-cli connect`

## 1. Scrape

```
cd /root/ig-sentiment
IG_PROXY=socks5://127.0.0.1:40000 ./venv/bin/python scrape.py \
  --url "https://www.instagram.com/p/XXXXX/" --out komentar.csv [--limit 200]
```

- Tanpa login, tanpa sessionid — jalur GraphQL publik via WARP.
- `--limit` disarankan; tanpa limit post besar bisa lama (pagination lambat).
- Output: `komentar.csv` (kolom: pk, username, text, likes, created_at, replied_to)

## 2. Sentiment

```
cd /root/ig-sentiment
HF_HOME=/root/ig-sentiment/hf ./venv/bin/python sentiment.py \
  --in komentar.csv --out berlabel.csv
```

Output: `berlabel.csv` + ringkasan persentase di layar.
Kecepatan VPS 2-core: ~5-10 menit per 100 komentar.

---

## Catatan

- Model: `w11wo/indonesian-roberta-base-sentiment-classifier` (IndoBERT,
  3 label: Positive/Neutral/Negative). Akurasi bagus untuk bahasa Indonesia
  formal; slang ekstrem kadang meleset — cek kolom `score`: di bawah 0.6
  anggap "tidak yakin".
- Keamanan sessionid: setara akses akun. Pakai akun cadangan. Cabut akses:
  Instagram -> Settings -> Account Center -> Password and security ->
  Where you're logged in -> logout device.
- Delay antar request sudah diset 1-3 detik. Jangan naikkan volume;
  akun bisa kena challenge/limit IG.
- Scraping melanggar ToS Instagram. Untuk riset internal/skala kecil umum
  dipakai, tapi risiko akun dibatasi ditanggung akun yang dipakai.
