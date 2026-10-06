# Sentimetter — Multi-Platform Sentiment Analysis

Dashboard web (Streamlit) untuk scrape komentar dari 6 platform sosial media,
klasifikasi sentimen pakai model IndoBERT, kategorisasi topik, visualisasi,
ringkasan AI, dan export PDF.

## Struktur File

Repo punya **2 alur** yang berjalan terpisah:

### Alur 1 — Dashboard Web (utama)

Dashboard Streamlit interaktif. Semua scraping + analisis jalan di dalam app.

```
app.py              Dashboard UI utama (Streamlit). 1075 baris.
                    Scrape → analisis sentimen → visualisasi → AI insight → PDF.
├── config.py       Konfigurasi: path, env vars, model LLM, model sentiment.
├── multiscrape.py  Scraper Instagram + YouTube + Web (Google News).
│   └── ig_web_scraper.py   Scraper IG via web API (pakai cookie session_id).
├── scrapers_extra.py       Scraper Facebook + TikTok + Play Store.
├── categorize.py   Klasifikasi kategori konten (Pelayanan/Klaim/Sistem Digital).
│                   Keyword matching + LLM fallback. Bisa dikustomisasi.
└── icons.py         Set SVG icon untuk UI (style seragam, tema docs).
```

Jalankan:
```
./venv/bin/streamlit run app.py --server.port 9120 --server.address 0.0.0.0
```

### Alur 2 — CLI Pipeline (otomatis via shell script / cron)

Pipeline command-line lama. Scrape → sentiment → ringkasan → kirim ke LINE bot.

```
run_pipeline.sh             run_keyword_pipeline.sh
  scrape.py (URL IG)          keyword_scrape.py (hashtag/keyword)
       ↓                            ↓
  sentiment.py              sentiment.py (CSV → CSV berlabel)
       ↓                            ↓
  summarize.py              summarize.py (ringkasan teks)
       ↓                            ↓
  line_send.py              line_send.py (kirim ke LINE + file CSV)
```

| File | Fungsi |
|---|---|
| `scrape.py` | Scraper IG per-URL postingan (pakai instagrapi). |
| `keyword_scrape.py` | Scraper IG berdasarkan hashtag/keyword. |
| `sentiment.py` | CLI: CSV komentar → CSV berlabel sentimen (model Roberta). |
| `summarize.py` | Generate ringkasan teks untuk pesan LINE. |
| `line_send.py` | Kirim ringkasan + file CSV ke LINE bot. |
| `scheduled_scrape.py` | Versi terjadwal untuk cron, simpan hasil ke `hasil/`. |

### Dokumentasi (`docs/`)

Bukan kode utama. Tool pendukung dokumentasi:

| File | Fungsi |
|---|---|
| `docs/make_diagram.py` | Generate diagram arsitektur PNG. |
| `docs/send_docs.py` | Kirim dokumen. |
| `docs/verify_pdf.py` | Verifikasi file PDF. |

## Setup VPS

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
