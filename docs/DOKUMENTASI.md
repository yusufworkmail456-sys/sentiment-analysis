# Dokumentasi Sistem Sentiment Analysis Multi-Source

**Hermes Agent + LINE Channel + Streamlit Sentiment Analysis**
VPS 69.5.22.24 · Domain publik: https://grumble-matchbook-dispersed.ngrok-free.dev
Versi: 23 September 2026

---

## 1. Ringkasan Sistem

Sistem ini menganalisis sentimen publik terhadap sebuah keyword (contoh use case: **taspen**) dari tiga sumber sekaligus — Instagram, YouTube, dan web berita — lalu menyajikan hasilnya sebagai grafik interaktif dan CSV berlabel.

Tiga komponen utama:

| Komponen | Peran | Teknologi |
|---|---|---|
| Hermes Agent | Otak sistem: gateway chat LINE, eksekusi pipeline, perawatan VPS | Hermes Agent (Nous Research) |
| LINE Channel | Antarmuka chat pengguna: kirim keyword/URL, terima hasil + link CSV | LINE Messaging API |
| Streamlit App | Antarmuka web: scrape + analisis mandiri, grafik, download CSV | Streamlit + Plotly, di-host di VPS |

Model sentimen: **w11wo/indonesian-roberta-base-sentiment-classifier** (IndoBERT, 3 label: Positif / Netral / Negatif), berjalan di CPU VPS.

---

## 2. Diagram Arsitektur

```
                                   ┌─────────────────────────────┐
                                   │   HP / Browser Pengguna     │
                                   └──────┬──────────────┬───────┘
                        kirim keyword/URL │              │ buka /sentiment/
                                          │              │ (password app)
                                   ┌──────▼──────┐  ┌────▼─────────────────┐
                                   │ LINE server │  │ ngrok (static domain)│
                                   └──────┬──────┘  └────┬─────────────────┘
                                          │ webhook      │ tunnel HTTPS
                                   ┌──────▼──────┐       │
                                   │ nginx :80   │◄──────┘
                                   │  ├─ /line/  → 127.0.0.1:8646 (gateway Hermes)
                                   │  ├─ /sentiment/ → 127.0.0.1:9120 (Streamlit)
                                   │  └─ /files/ → /var/www/ig-files (CSV hasil)
                                   └──────┬──────┘
                                          │
                                   ┌──────▼───────────────────────┐
                                   │ Hermes Agent (gateway+agent) │
                                   │  - terima chat LINE          │
                                   │  - jalankan pipeline         │
                                   │  - push hasil ke LINE        │
                                   └──────┬───────────────────────┘
                                          │
              ┌───────────────────────────┼────────────────────────────┐
              │                           │                            │
     ┌────────▼────────┐        ┌─────────▼─────────┐        ┌─────────▼─────────┐
     │ scrape_ig       │        │ scrape_yt         │        │ scrape_web        │
     │ IG via WARP     │        │ yt-dlp + comment  │        │ Bing News RSS     │
     │ (login ig_session)│      │ downloader        │        │ + trafilatura     │
     └────────┬────────┘        └─────────┬─────────┘        └─────────┬─────────┘
              │                           │                            │
              └───────────────────────────┼────────────────────────────┘
                                          ▼
                              ┌───────────────────────────┐
                              │ Sentiment IndoBERT (CPU)  │
                              │ 3 label + skor            │
                              └────────────┬──────────────┘
                                           ▼
                          ┌──────────────────────────────────┐
                          │ Output: CSV berlabel + grafik    │
                          │ - Streamlit: pie/bar/tren/contoh │
                          │ - LINE: ringkasan + link CSV     │
                          └──────────────────────────────────┘
```

Kunci teknis: **Instagram memblokir IP datacenter** (VPS) — semua request IG dari VPS harus lewat **Cloudflare WARP** (SOCKS5 127.0.0.1:40000) supaya egress-nya jadi IP Cloudflare, bukan IP VPS.

---

## 3. Komponen & Layanan di VPS

### 3.1 Layanan systemd (semua auto-start saat boot)

| Layanan | Tipe | Port/Path | Fungsi |
|---|---|---|---|
| `hermes-gateway` | user systemd | :8646 | Gateway webhook LINE |
| `hermes-dashboard` | user systemd | :9119 | Dashboard Hermes |
| `sentiment-ui` | user systemd | :9120 | Streamlit sentiment app |
| `ngrok-tunnel` | user systemd | — | Tunnel ke domain statis ngrok |
| `nginx` | system systemd | :80 | Router: /line/, /sentiment/, /files/ |
| `warp-svc` | system systemd | SOCKS5 :40000 | Proxy egress IG |

Semua user service: `systemctl --user status <nama>` · enable + linger on → hidup lagi sendiri setelah reboot.

### 3.2 File penting di /root/ig-sentiment/

| File | Fungsi |
|---|---|
| `multiscrape.py` | Scraper 3 sumber (IG/YouTube/Web) — dipakai Streamlit |
| `app.py` | UI Streamlit |
| `sentiment.py` | Labeling IndoBERT (CLI) |
| `keyword_scrape.py` | Scraper IG by keyword (CLI, khusus IG) |
| `run_pipeline.sh` | One-shot: URL post IG → scrape+sentiment+LINE push |
| `run_keyword_pipeline.sh "<tag>" N M` | One-shot: keyword → LINE push |
| `line_send.py` | Kirim pesan + host CSV ke LINE |
| `summarize.py` | Ringkasan teks hasil |
| `ig_session.json` | Sesi login IG (dibuat saat login) |
| `hasil/` | CSV hasil (komentar + berlabel) |
| `hf/` | Cache model IndoBERT (~500MB) |

### 3.3 Konfigurasi nginx

`/etc/nginx/sites-enabled/hermes-dashboard` meng-include snippet:

| Snippet | Route |
|---|---|
| `line-webhook.conf` | `/line/` → 127.0.0.1:8646 |
| `sentiment-ui.conf` | `/sentiment/` → 127.0.0.1:9120 |
| `ig-files.conf` | `/files/` → /var/www/ig-files, gate `?key=IG_FILES_KEY` |

---

## 3.3a Perawatan Rutin — referensi, jalankan hanya saat dibutuhkan

### a. Cek kesehatan sistem

```bash
systemctl --user status hermes-gateway hermes-dashboard sentiment-ui ngrok-tunnel
systemctl status nginx warp-svc
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:9120/sentiment/
curl -s -o /dev/null -w "%{http_code}\n" -H "ngrok-skip-browser-warning: 1" \
  https://grumble-matchbook-dispersed.ngrok-free.dev/sentiment/
```

### b. Kalau popup "Connection failed with status 404" muncul di /sentiment/

Artinya tunnel ngrok putus (BUKAN app mati). Urutan cek:

```bash
journalctl --user -u ngrok-tunnel --since "30 min ago" | tail -20
uptime; free -m          # load tinggi + RAM penuh = penyebab klasik
systemctl --user restart ngrok-tunnel
```

Insiden 23 Sep 2026: VM 2GB tanpa swap + model IndoBERT (~700MB RSS) → RAM habis → load 25 → ngrok reconnect timeout → tunnel drop → popup 404. **Fix permanen yang sudah dipasang: swap 2GB di /swapfile (persist di /etc/fstab) + vm.swappiness=10.**

### c. Kalau IG gagal (LoginRequired) di log scraping

Sesi IG expired (terbukti bisa dalam hitungan jam). Login ulang:

```bash
cd /root/ig-sentiment && IG_PROXY=socks5://127.0.0.1:40000 ./venv/bin/python - <<'PY'
from instagrapi import Client
cl = Client(); cl.delay_range=[1,3]
cl.set_proxy('socks5://127.0.0.1:40000')
cl.login('USERNAME', 'PASSWORD')
cl.dump_settings('ig_session.json')
print('ok', cl.account_info().username)
PY
```

Setelah login, IG kirim notif "unrecognized device" ke HP — abaikan, jangan tap "bukan saya". Kalau muncul challenge kode verifikasi: throttle IG aktif, tunggu 4+ menit antar percobaan.

### d. Kalau LINE bot tidak merespons

```bash
systemctl --user status hermes-gateway
journalctl --user -u hermes-gateway --since "30 min ago" | tail -20
```

---

## 4. Cara Pakai — Streamlit (via HP atau PC)

1. Buka https://grumble-matchbook-dispersed.ngrok-free.dev/sentiment/ (browser HP akan minta password app — sekali saja).
2. Sidebar: isi **Keyword** (mis. `taspen`), atur slider jumlah per source (IG / YouTube / Web).
3. Klik **Mulai Scrape + Analisis**.
4. Tunggu: scraping (menit) → "Memuat model" pertama kali ~1 menit (normal, jangan refresh) → inference ~0.5–1 detik per komentar.
5. Hasil: metrik total/positif/netral/negatif, pie chart, bar per source, tren per hari, contoh komentar teratas per label, preview 10 baris, tombol **Download CSV**.

Kolom CSV: `source, text, author, date, likes, url, label, score`.

Dari Chrome HP: menu ⋮ → **Add to Home screen** → app terpasang seperti aplikasi native.

---

## 5. Cara Pakai — LINE Channel

**Via chat ke bot LINE (@749dqfbn):**
- Kirim URL post IG → pipeline one-shot jalan (scrape → sentiment → ringkasan + link CSV balik ke LINE).
- Kirim keyword (mis. `scrape #taspen`) → pipeline keyword jalan, hasil balik ke LINE.

**Via perintah di VPS (hasil push ke LINE):**
```bash
cd /root/ig-sentiment
./run_pipeline.sh "https://www.instagram.com/p/CODE/" 100     # URL post
./run_keyword_pipeline.sh "taspen" 5 30                       # keyword, 5 post, 30 komentar/post
```

**Catatan LINE:** LINE tidak bisa kirim attachment file — CSV selalu dikirim sebagai **link download** (hosting /files/, digate `?key=`).

---

## 6. Cara Pakai — Hermes Agent (chat ini)

Hermes di VPS ini bisa mengoperasikan semuanya lewat chat: jalankan pipeline, cek layanan, login ulang IG, restart tunnel, perbaiki insiden. Contoh permintaan:

- "scrape #taspen 5 postingan, kirim ke LINE"
- "cek kenapa sentiment app 404"
- "login ulang IG, creds: ..." (password tidak disimpan di chat maupun file)
- "restart sentiment-ui"

---

## 7. Model Sentimen

| Aspek | Detail |
|---|---|
| Model | w11wo/indonesian-roberta-base-sentiment-classifier |
| Label | Positive / Neutral / Negative (ditampilkan sebagai Positif/Netral/Negatif) |
| Ukuran | ~500MB, cache di /root/ig-sentiment/hf |
| Kecepatan | ~0.5–1 detik per komentar (CPU 2-core, batch 16) |
| Kelemahan | Slang ("mantab", "goks") sering salah label dengan skor rendah; skor < 0.6 = tidak pasti |

---

## 8. Keamanan

| Hal | Status |
|---|---|
| Login IG | Password tidak pernah disimpan; yang tersimpan hanya sesi (`ig_session.json`) |
| LINE credentials | Di /root/.hermes/.env, tidak pernah masuk chat/log |
| CSV hasil | Publik tapi digate `?key=IG_FILES_KEY` |
| /sentiment/ | Saat ini TANPA password — direncanakan: basic auth nginx + form login IG di dalam app |
| Egress IG | Selalu via WARP (IP Cloudflare), bukan IP VPS |

---

## 9. Batasan & Hal yang Perlu Diketahui

- **IG sesi cepat expired** (bisa hitungan jam) — login ulang sesekali.
- **Hashtag search IG wajib login**; scraping komentar per-post bisa tanpa login (via WARP).
- **Web = isi artikel berita**, bukan komentar (media Indonesia umumnya tak punya kolom komentar publik).
- **YouTube**: komentar via yt-dlp + youtube-comment-downloader, tanpa API key.
- **X/Twitter & Facebook**: tidak didukung (login wall, tidak reliable).
- **VM 2 core / 2GB RAM + swap 2GB**: jangan jalankan dua analisis besar paralel; slider jangan langsung di-max.
- **Slang Indonesia**: skor < 0.6 dianggap tidak pasti.

---

## 10. Quick Reference

| Kebutuhan | Perintah |
|---|---|
| Cek semua layanan | `systemctl --user status hermes-gateway hermes-dashboard sentiment-ui ngrok-tunnel` |
| Restart Streamlit | `systemctl --user restart sentiment-ui` |
| Restart tunnel | `systemctl --user restart ngrok-tunnel` |
| Cek WARP | `warp-cli status` + `curl -s --socks5-hostname 127.0.0.1:40000 ifconfig.me` |
| Pipeline keyword → LINE | `./run_keyword_pipeline.sh "taspen" 5 30` |
| Pipeline URL → LINE | `./run_pipeline.sh "<url>" 100` |
| Sentiment CLI | `HF_HOME=/root/ig-sentiment/hf ./venv/bin/python sentiment.py --in komentar.csv --out berlabel.csv` |
| Kirim file ke LINE | `./venv/bin/python line_send.py --to Ub74d3487b50860ee199e86c67b8ee99b --text "..." --file <csv>` |
| Log ngrok | `journalctl --user -u ngrok-tunnel --since "30 min ago"` |
| Log Streamlit | `journalctl --user -u sentiment-ui --since "30 min ago"` |

---

*Dokumentasi dibuat otomatis oleh Hermes Agent, 23 September 2026.*
