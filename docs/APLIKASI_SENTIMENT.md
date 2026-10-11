# Taspen Sentiment Platform — Dokumentasi Aplikasi

**Versi dokumen:** mengikuti versi aplikasi (saat ini **v2.2.0**)
**Stack:** FastAPI + Vanilla JS (frontend) + IndoBERT (sentiment) + LLM (AI Insight)
**Demo:** http://69.5.22.42/
**Repositori:** https://github.com/yusufworkmail456-sys/sentiment-analysis (branch `fastapi-ui`)
**Kredit:** Aku Mitra Digital

---

## 1. Ringkasan Aplikasi

Taspen Sentiment Platform adalah aplikasi web untuk **memantau persepsi publik** terhadap Taspen di media sosial dan platform digital. Alur kerjanya:

1. **Scrape** komentar publik dari 6 sumber: Instagram, YouTube, Facebook, TikTok, Web/artikel berita, dan Google Play Store.
2. **Analisis sentimen** setiap komentar dengan model NLP berbahasa Indonesia (IndoBERT): label **Positif / Netral / Negatif** + skor keyakinan.
3. **Kategorisasi domain** (Klaim, Pelayanan, Sistem Digital, dll.), **deteksi bot/spam**, dan **tagging pihak/entitas** yang disebut.
4. **Visualisasi** hasil dalam dashboard interaktif + **AI Insight** (ringkasan eksekutif, rekomendasi, chatbot tanya-jawab data).
5. **Ekspor** hasil ke CSV/PDF untuk pelaporan.

### Halaman (navbar)

| Halaman | Fungsi |
|---|---|
| **Scrape & Analysis** | Input keyword atau URL postingan → jalankan scrape + analisis. Ada log live, riwayat scrape (retensi 6 jam), dan tabel hasil. |
| **Visualization Overview** | Ringkasan agregat dari seluruh data historis: distribusi sentimen, tren waktu, perbandingan antar keyword. |
| **Per-Source Breakdown** | Analisis per platform (IG vs YT vs FB, dst.) — GSS per sumber, kata kunci, entitas. |
| **Historical Analytics** | Data hasil scrape terjadwal (otomatis tiap 6 jam, keyword `taspen`) — tren jangka panjang. |
| **AI Insight** | Ringkasan eksekutif, rekomendasi, dan chatbot berbasis LLM yang membaca data hasil analisis. |

Sidebar kiri menampilkan: status model AI, versi aplikasi (`v2.2.0`), kartu **Data Teranalisis** (volume baris yang sudah dianalisis), dan di bawahnya credit **Aku Mitra Digital**.

---

## 2. Fitur

### 2.1 Scrape by Keyword
- Input satu keyword, target jumlah per platform dapat diatur (IG/YT/Web/Play Store/FB/TikTok).
- Toggle **Deteksi bot/spam** dan **Tag entity mentions** (default aktif).
- Target "dikejar": kalau hasil kurang dari target (komentar duplikat dibuang / stok platform habis), scraper otomatis mengulang dengan over-fetch sampai target tercapai atau stok benar-benar habis.
- Expander **"Aturan Deteksi Bot & Entity (aktif)"** menampilkan aturan yang sedang aktif (keyword bot, pola teks, pola username, kamus entitas).

### 2.2 Scrape per Post URL
- Tempel URL satu postingan, pilih platform, tentukan jumlah komentar (10–500).
- Format URL yang didukung antara lain:
  - YouTube: `youtu.be/<id>`, `youtube.com/watch?v=<id>` (parameter `?si=...` aman diabaikan)
  - Facebook: `facebook.com/share/p/...` maupun `facebook.com/<halaman>/posts/<id>` (link share otomatis mengikuti redirect)
  - Instagram: `instagram.com/p/<code>`
  - TikTok: `tiktok.com/@user/video/<id>` + link pendek `vt.tiktok.com`
  - Play Store: URL halaman aplikasi (ambil ulasan)
  - Web: URL artikel berita (komentar = isi artikel, 1 baris)
- Toggle deteksi bot & entity + expander aturan, sama dengan mode keyword.
- Jika komentar sebuah video YouTube dinonaktifkan oleh pembuatnya, aplikasi memberi pesan yang jelas, bukan error kosong.

### 2.3 Hasil & Visualisasi (tiap halaman)
Setiap visualisasi disajikan dalam kartu berjudul + caption. Ringkasan isi:

| Visualisasi | Penjelasan |
|---|---|
| **Donut distribusi sentimen** | Proporsi Positif/Netral/Negatif dari seluruh komentar hasil scrape. |
| **Time series sentimen** | Tren 3 label sepanjang waktu (berdasarkan tanggal komentar). Dropdown rentang waktu ada di section time series (ekspektasi scope = 2 tren). |
| **Bar per kategori (GSS)** | Jumlah komentar per kategori domain (Klaim, Pelayanan, dst.) — menunjukkan topik apa yang paling banyak dibicarakan. |
| **GSS per sumber** | Perbandingan kategori antar platform — mis. klaim lebih ramai di FB, sistem digital lebih ramai di Play Store. |
| **Asli vs dugaan bot per sumber** | Bar dua warna: komentar wajar vs terflag bot, per platform. |
| **Top komentar (cards)** | Komentar dengan likes tertinggi + komentar terflag bot beserta alasan pendeteksinya (`bot_reasons`). |
| **Penyebutan pihak lain** | Entitas non-Taspen yang ikut disebut (pesaing/regulator/media), dikelompokkan per kategori. |
| **Tren historis (Historical Analytics)** | Gabungan seluruh run terjadwal — memantau arah sentimen mingguan/bulanan. |

### 2.4 AI Insight (LLM)
- **Ringkasan eksekutif** dan **rekomendasi** yang dihasilkan LLM dari data teranalisis.
- **Chatbot**: tanya jawab bebas tentang data (mode *session* = snapshot scrape terakhir; mode *historical* = seluruh database).
- LLM dipanggil via API OpenAI-compatible (dikonfigurasi lewat `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` di `.env`).

### 2.5 Ekspor
- **CSV** tiap run (tersimpan di `hasil/` + bisa diunduh dari Riwayat Scrape).
- **PDF** laporan siap-cetak dari halaman hasil.

---

## 3. Mekanisme Scrape (teknis)

Semua scraper ada di `multiscrape.py`, terdaftar di dict `URL_SCRAPERS` (per-URL) dan fungsi `scrape_*` (per-keyword).

| Sumber | Mekanisme | Catatan |
|---|---|---|
| **Instagram** | `instagrapi` (Private API). Per-keyword: hashtag search → post teratas → komentar. Per-URL: shortcode → media_id → komentar. | Wajib login (session `sessionid`). IG memblokir IP datacenter → proxy WARP SOCKS5 (`IG_PROXY`) sangat disarankan. Session bisa expired cepat (jam, bukan hari). |
| **YouTube** | Parse `ytInitialData` dari HTML watch page → ambil continuation token → POST `youtubei/v1/next` → parsing `commentEntityPayload` (teks, author, waktu, likes). | Tahan terhadap layout A/B YouTube. Sort menu dipakai untuk ambil urutan "Terbaru". Video dengan komentar dinonaktifkan dikenali dan dilaporkan. |
| **Facebook** | Playwright (headless Chromium) + cookie login (`c_user` + `xs`). Share link di-follow redirect-nya. Scroll untuk lazy-load, klik "View more comments"/"Lihat komentar lainnya"/"View more replies"/"Balas lainnya". | Komentar diekstrak dari elemen `aria-label="Comment by <nama> <waktu>"` / `"Komentar oleh ..."` — author di-parse dari label. Dedupe teks. |
| **TikTok** | `TikTokApi` async + `ms_token`. Link pendek di-resolve dulu via redirect HEAD. | Wajib `ms_token` valid. |
| **Web/artikel** | `trafilatura` — ekstraksi isi artikel. | Dipakai sebagai konteks, 1 artikel = 1 baris. |
| **Play Store** | `google-play-scraper` — ulasan aplikasi. | Package app dikonfigurasi lewat env `PLAYSTORE_APP_1..N`. |

**Anti-duplikat:** `dedupe()` membuang komentar identik (teks + author).
**Chase target:** jumlah hasil dibandingkan target; bila kurang, scraper over-fetch dan diulang (maks beberapa kali) sampai target tercapai atau stok habis. Capaian per sumber dilaporkan di log.
**Sesi/credentials:** disimpan via halaman Scrape (expander "Kredensial Sumber Data") → endpoint `/api/sessions/*` → file di folder `sessions/`. Status kredensial tampil sebagai tile.

### 3.1 Deteksi Bot/Spam (heuristik, `categorize.py`)
Skor per komentar; dugaan bot bila skor ≥ threshold (default 2):
- **Pola username** (regex, mis. kombinasi angka-huruf acak, nama generik + angka).
- **Pola teks** (mis. hanya emoji, link WA/Telegram/shortener, istilah judi "wd/jp").
- **Keyword bot/spam**: promo, jual followers, endorse, judi online (judol), slot gacor, dll. — setiap keyword yang kena menambah skor.
- **Sangat pendek + likes tinggi** dan **konten tidak bermakna**.
Hasil: kolom `is_bot_suspect` + `bot_reasons` (alasan keterbacaan manusia).

### 3.2 Kategorisasi Domain (ABSAl-style, keyword + LLM fallback)
Kategori aktif: **Pelayanan, Klaim, Sistem Digital, Produk, Iuran/Potongan, Kantor Cabang, Penipuan/Misinformasi, Lainnya**.
- Keyword matching berbobot (keyword lebih panjang = bobot lebih besar); kategori dengan skor tertinggi menang; confidence = proporsi skor.
- Kalau tidak ada keyword yang cocok dan LLM tersedia, teks diklasifikasikan LLM (confidence 0.5). Tanpa LLM → "Lainnya".

### 3.3 Tagging Entitas
Kamus `ENTITY_DICT` per kategori: **Politik, Pemerintah/Regulasi, BUMN/Korporat, Media**. Teks di-scan (case-insensitive); entitas yang disebut disimpan di `entity_mentions` + `entity_categories` → dipakai untuk visualisasi "penyebutan pihak lain".

---

## 4. Mekanisme Sentiment Analysis (teknis)

`core.py` → `run_sentiment(df)`:
1. **Model**: `w11wo/indonesian-roberta-base-sentiment-classifier` (RoBERTa-base IndoBERT, 3 label). Di-load sekali dan di-cache. Jalankan di CPU; cache model di `HF_HOME` (offline mode).
2. **Inference** per batch 16 komentar → label mentah (`positive/neutral/negative`) dipetakan ke label Indonesia, skor disimpan 4 desimal.
3. **Keyakinan**: skor ≥ 0.6 = "yakin", di bawahnya = "ragu" (tampilkan hati-hati, sering terjadi pada slang/typo).
4. **Post-processing** (bila toggle aktif): kategorisasi domain, deteksi bot, tagging entitas (bagian 3.1–3.3).
5. Output kolom per baris: `source, text, author, date, likes, url, label, score, keyakinan, kategori, kategori_conf, is_bot_suspect, bot_reasons, entity_mentions, entity_categories`.

Kinerja acuan (VPS 2 vCPU / 4 GB RAM): ± 0.3–1 detik per batch → 100 komentar ± 30–60 detik termasuk scrape.

---

## 5. Cara Menggunakan

1. Buka **http://69.5.22.42/** (atau domain/IP server Anda).
2. Pastikan tile kredensial platform yang mau dipakai berstatus terisi (expander **Kredensial Sumber Data** di halaman Scrape & Analysis). IG butuh `sessionid`, FB butuh cookie `c_user`+`xs`, TikTok butuh `ms_token`. YouTube, Web, dan Play Store tidak butuh login.
3. **Mode keyword**: isi keyword (mis. `taspen`), atur target per platform, aktifkan/nonaktifkan deteksi bot & entity, klik **Mulai Scrape + Analisis**.
4. **Mode URL**: buka tab **Scrape per Post URL**, tempel URL postingan, pilih platform, tentukan jumlah komentar, klik **Scrape URL + Analisis**.
5. Pantau **Log Scrape** (live) dan **Riwayat Scrape** (6 jam; bisa unduh CSV per run).
6. Hasil tampil di bawah: KPI, grafik, tabel komentar, trust section (bot + entitas).
7. Lanjut ke **Visualization Overview** / **Per-Source Breakdown** / **Historical Analytics** untuk analisis lintas-run, atau **AI Insight** untuk ringkasan/rekomendasi/chatbot.
8. Unduh CSV dari riwayat, atau PDF dari halaman hasil.

Tips:
- Skor < 0.6 ("ragu") pada komentar slang jangan langsung dipercaya — cek manual.
- Kalau hasil keyword kecil, cek log: bisa jadi stok komentar platform memang habis atau semua duplikat.
- Kredensial IG yang expired biasanya muncul sebagai 0 komentar + error login di log → perbarui session.

---

## 6. Deploy ke Server Baru (step-by-step)

Kebutuhan: Ubuntu 22.04/24.04, 2 vCPU, ≥ 4 GB RAM + swap 2 GB (model IndoBERT ~700 MB di memori saat inference), akses root, port 80 terbuka.

### 6.1 Paket sistem
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3.12-venv python3-pip git nginx curl
# Swap 2 GB (wajib di VPS kecil)
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 6.2 Kode aplikasi
```bash
sudo mkdir -p /opt/sentimetter-fastapi && cd /opt/sentimetter-fastapi
sudo git clone -b fastapi-ui https://github.com/yusufworkmail456-sys/sentiment-analysis.git repo
cd repo
```

### 6.3 Virtualenv + dependensi
```bash
sudo python3.12 -m venv /opt/sentimetter/venv
sudo /opt/sentimetter/venv/bin/pip install --upgrade pip
sudo /opt/sentimetter/venv/bin/pip install -r requirements-fastapi.txt
# catatan: versi di requirements-fastapi.txt lama; kalau ada konflik, pakai versi yang sudah terbukti:
#   fastapi, uvicorn, pandas, transformers>=5, torch (CPU), instagrapi==2.2.1,
#   TikTokApi==7.3.2, playwright==1.61, youtube-comment-downloader, trafilatura,
#   google-play-scraper, apscheduler, dateparser, python-dotenv, httpx, fpdf2
sudo /opt/sentimetter/venv/bin/playwright install chromium   # untuk scraper Facebook
```

### 6.4 Konfigurasi `.env`
```bash
sudo nano /opt/sentimetter-fastapi/repo/.env
```
Isi:
```ini
SENTIMENT_MODEL=w11wo/indonesian-roberta-base-sentiment-classifier
LLM_BASE_URL=<endpoint OpenAI-compatible, mis. https://ark.ap-southeast.bytepluses.com/api/v3>
LLM_MODEL=<nama model LLM>
LLM_API_KEY=<API key LLM>
APP_TITLE=Sentimetter
APP_SUBTITLE=Multi-platform · IndoBERT · AI insight
# opsional:
IG_PROXY=socks5://127.0.0.1:40000        # proxy WARP utk Instagram
PLAYSTORE_APP_1=<package aplikasi>       # Play Store scraping
SCHEDULE_ENABLED=1
SCHEDULE_KEYWORDS=taspen
SCHEDULE_INTERVAL_HOURS=6
```

### 6.5 Folder runtime + model cache
```bash
sudo mkdir -p /opt/sentimetter/hf /opt/sentimetter-fastapi/repo/hasil /opt/sentimetter-fastapi/repo/sessions
# Model IndoBERT akan ter-download otomatis saat run pertama (±500 MB).
# Jalankan sekali manual supaya offline-mode selanjutnya aman:
cd /opt/sentimetter-fastapi/repo && sudo -E HF_HOME=/opt/sentimetter/hf /opt/sentimetter/venv/bin/python -c "from transformers import pipeline; pipeline('text-classification', model='w11wo/indonesian-roberta-base-sentiment-classifier')"
```

### 6.6 Systemd service
```bash
sudo tee /etc/systemd/system/sentimetter.service > /dev/null <<'EOF'
[Unit]
Description=Sentimetter FastAPI
After=network.target

[Service]
WorkingDirectory=/opt/sentimetter-fastapi/repo
Environment=HF_HOME=/opt/sentimetter/hf
Environment=HF_HUB_OFFLINE=1
Environment=TRANSFORMERS_OFFLINE=1
ExecStart=/opt/sentimetter/venv/bin/uvicorn main:app --host 127.0.0.1 --port 9120
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sentimetter
```
> Catatan: `HF_HUB_OFFLINE=1` mengharuskan model sudah ter-cache di 6.5.

### 6.7 Nginx (reverse proxy port 80)
```bash
sudo tee /etc/nginx/sites-available/sentimetter > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:9120;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400s;
        proxy_buffering off;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/sentimetter /etc/nginx/sites-enabled/sentimetter
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 6.8 Verify
```bash
systemctl is-active sentimetter
curl -s http://127.0.0.1:9120/api/app/info     # {"ok":true,"version":"2.2.0",...}
curl -s http://127.0.0.1/ | head -5            # index.html ter-serve
```
Buka `http://<IP-server>/` di browser → halaman Scrape & Analysis tampil, sidebar menampilkan versi `v2.2.0`.

### 6.9 (Opsional) Instagram via Cloudflare WARP
```bash
curl -fsSL https://pkg.cloudflareclient.com/install.sh | sudo bash
warp-cli registration new
warp-cli mode proxy
warp-cli connect            # SOCKS5 di 127.0.0.1:40000
# pastikan IG_PROXY=socks5://127.0.0.1:40000 ada di .env, lalu restart sentimetter
```

### 6.10 (Opsional) Update aplikasi
```bash
cd /opt/sentimetter-fastapi/repo
sudo git pull origin fastapi-ui
sudo systemctl restart sentimetter
# Cek versi baru via /api/app/info — angka versi ikut tampil di sidebar.
```

---

## 7. Troubleshooting singkat

| Gejala | Sebab umum | Solusi |
|---|---|---|
| IG selalu 0 komentar / login_required | Session expired atau IG blok IP datacenter | Perbarui sessionid; aktifkan proxy WARP |
| FB "Cookie tidak lengkap" | Cookie tanpa `c_user`/`xs` atau expired | Ambil cookie login terbaru dari browser |
| YouTube "0 komentar" pada video tertentu | Komentar video dinonaktifkan pembuat | Normal — coba video lain |
| `ImportError: pipeline from transformers` sesekali | Flaky import saat burst (transformers 5.x) | Ulangi request; biasanya berhasil |
| Aplikasi OOM / restart sendiri | RAM habis saat inference | Pastikan swap 2 GB aktif; kurangi limit scrape |
| Waktu scrape lama | Model CPU + chase target | Normal untuk 100+ komentar; turunkan target bila perlu |

---

*Dokumen ini menjelaskan aplikasi versi 2.2.0. Perbarui nomor versi di bagian atas setiap kali aplikasi di-update (config.py `APP_VERSION` + main.py FastAPI version).*
