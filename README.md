# Multi-Platform Sentiment Analysis

A self-service web application for scraping, analyzing, and visualizing public sentiment across multiple social media platforms — with AI-powered executive summaries and PDF report export.

## Overview

This tool scrapes comments and reviews from **6 platforms** (Instagram, YouTube, Web news, Google Play Store, Facebook, TikTok), runs them through an IndoBERT sentiment classification model, categorizes them by domain topic, and presents the results in an interactive dashboard with AI-generated insights.

Built with **Streamlit**, **Plotly**, **HuggingFace Transformers**, and any OpenAI-compatible LLM API.

## Features

- **Multi-Platform Scraping** — Instagram, YouTube, Web news, Play Store (no login), Facebook, TikTok
- **IndoBERT Sentiment Model** — Indonesian-language sentiment classification (configurable to any HuggingFace model)
- **Domain Categorization** — Configurable keyword-based topic classification
- **8 Dashboard Visualizations**:
  - GSS Score Gauge (0-100)
  - ABSA Diverging Bar (sentiment per category)
  - Per-Source Stacked Bar (sentiment distribution per platform)
  - Channel Scorecard (ranking table with GSS per platform)
  - Top Terms (most frequent words in negative comments)
  - Viral Detection (scatter plot of engagement vs sentiment)
  - Trend Volume (monthly comment volume over time)
  - GSS Trend (sentiment score over time)
- **AI Insight Panel** — Executive summary + strategic recommendations via LLM
- **AI Chatbot** — Ask questions about the data, with reasoning shown for models that support it (e.g. GLM, DeepSeek-R1)
- **PDF Export** — Full report with all charts + AI insights
- **Alert Badges** — Automatic red flags for categories with >50% negative sentiment
- **Data Filtering** — Filter by source, sentiment, category, text search
- **CSV Export** — Download raw data

## How to Deploy

### Prerequisites

- Python 3.10+
- 2GB+ RAM (for sentiment model)
- Linux server (Ubuntu/Debian recommended)

### Step 1: Clone & Setup

```bash
git clone https://github.com/yusufworkmail456-sys/sentiment-analysis.git
cd sentiment-analysis
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note on torch:** `requirements.txt` installs the default torch build. If you're on a CPU-only server and want to avoid downloading CUDA packages (saves ~2GB), install torch first:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### Step 2: Install Playwright (for TikTok scraper)

```bash
playwright install --with-deps chromium
```

### Step 3: Download Fonts

The app uses DejaVuSans fonts for PDF export and wordclouds:

```bash
mkdir -p assets/fonts
# On Debian/Ubuntu:
cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf assets/fonts/
cp /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf assets/fonts/
# Or install: apt install fonts-dejavu-core
# Or download from: https://dejavu-fonts.github.io/
```

### Step 4: Configure Environment

```bash
cp .env.example .env
nano .env
```

Set these variables:
- `LLM_BASE_URL` — Your LLM API endpoint (OpenAI, Ollama, vLLM, ByteDance ARK, etc.)
- `LLM_MODEL` — Model name (e.g., `gpt-4o-mini`, `llama3`, `glm-5-3-flash-260828`, etc.)
- `LLM_API_KEY` — API key (leave empty for local models like Ollama)
- `SENTIMENT_MODEL` — HuggingFace model (default: Indonesian Roberta)
- `APP_TITLE` — Your app title
- `APP_SUBTITLE` — Subtitle shown under title
- `PLAYSTORE_APP_1`..`PLAYSTORE_APP_5` — (Optional) Pre-configure Play Store app package IDs

### Step 5: Run

```bash
./venv/bin/streamlit run app.py --server.port 9120 --server.address 0.0.0.0 --server.headless true
```

Access at `http://YOUR_SERVER_IP:9120`. Open port 9120 in your cloud provider's security group / firewall if needed.

### Step 6: Systemd Service (Auto-start on boot)

```ini
# /etc/systemd/system/sentimetter.service
[Unit]
Description=Sentimetter - Multi-Platform Sentiment Analysis
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sentimetter
Environment=HF_HOME=/opt/sentimetter/hf
ExecStart=/opt/sentimetter/venv/bin/streamlit run app.py \
    --server.port 9120 \
    --server.address 0.0.0.0 \
    --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now sentimetter
systemctl status sentimetter
```

### Step 7: Nginx Reverse Proxy (Optional — for domain + HTTPS)

If you have a domain and want HTTPS access:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:9120;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_buffering off;
    }
}
```

```bash
# HTTPS via Let's Encrypt:
certbot --nginx -d your-domain.com
```

Then change `--server.address` back to `127.0.0.1` in the systemd service.

## How to Use

1. **Open the web app** in your browser

2. **Configure credentials** (optional) — Click "Kredensial Sumber Data" to enter:
   - Instagram: username + password
   - Facebook: session cookie (`c_user`, `xs`, etc.)
   - TikTok: `ms_token`
   - Play Store, YouTube, Web: no login needed

3. **Enter a keyword** — e.g., your brand name, product, or topic

4. **Select sources** — Toggle which platforms to scrape (IG, YT, Web, Play Store, FB, TikTok)

5. **Click "Mulai Scrape + Analisis"** — The app scrapes, classifies sentiment, and categorizes

6. **View Dashboard** — 8 visualizations with alert badges, trends, and scorecards

7. **Generate AI Insights** — Click "🤖 AI" button → "Generate All AI Insights" for executive summary + recommendations

8. **Export PDF** — Click "Export PDF" for a full report with charts + AI insights

9. **Chat with AI** — Ask follow-up questions about the data in the AI panel. Models that return reasoning (e.g. GLM, DeepSeek-R1) will show their reasoning process.

## Security Notes

- **Credentials are stored locally** in `sessions/` directory as JSON files. They never leave your server.
- **LLM API key** is read from `.env` file via `config.py`. Never commit `.env` to git (it's in `.gitignore`).
- **No data persistence** — Scraped data exists only in the current browser session. Refreshing the page clears it.
- **No external data sharing** — Comments are sent to the LLM API for summary generation only. No third-party analytics or tracking.
- **Play Store & YouTube** scrapers require no authentication.
- **Facebook & TikTok** require session tokens — handle with care, treat them like passwords.
- **Rate limiting** — Be mindful of platform API limits. Use reasonable `max` values per source.

## Limitations

- **Language**: Default sentiment model is Indonesian (`w11wo/indonesian-roberta-base-sentiment-classifier`). Change `SENTIMENT_MODEL` in `.env` for other languages.
- **Platform API limits**:
  - Instagram: May require proxy; frequently rate-limited
  - YouTube: Comment count limited by `youtube-comment-downloader`
  - Facebook: Cookie-based; may break when Facebook changes its DOM
  - TikTok: `ms_token` expires frequently; requires Playwright
  - Play Store: Limited to reviews available via `google-play-scraper`
  - Web: Depends on `trafilatura` RSS/article parsing
- **Model accuracy**: IndoBERT achieves ~85% on Indonesian sentiment. Low-confidence predictions (< 0.6) are flagged as "ragu".
- **No real-time monitoring**: This is a snapshot tool, not a continuous monitoring pipeline.
- **Single-user**: Not designed for concurrent users. Each session is independent.
- **Trend visualization**: Requires scraped data to have valid timestamps. Not all platforms provide reliable timestamps.

## Customization

### Domain Categories

Edit `categorize.py` — modify the `CATEGORIES` dictionary with your domain keywords:

```python
CATEGORIES = {
    "Customer Service": ["layanan", "cs", "antri", "ramah", "kasar", ...],
    "Product": ["produk", "kualitas", "rusak", "garansi", ...],
    "Pricing": ["harga", "mahal", "murah", "diskon", ...],
    # Add your own categories
}
```

### Play Store Apps

Add your app IDs to `.env` (optional — if not set, the app searches Play Store by keyword):

```env
PLAYSTORE_APP_1=com.yourcompany.app1
PLAYSTORE_APP_2=com.yourcompany.app2
```

### Sentiment Model

Change to any HuggingFace sentiment model:

```env
SENTIMENT_MODEL=cardiffnlp/twitter-roberta-base-sentiment
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| Charts | Plotly |
| Sentiment Model | HuggingFace Transformers (IndoBERT) |
| PDF Export | kaleido + fpdf2 |
| LLM | Any OpenAI-compatible API |
| IG Scraper | instagrapi |
| YT Scraper | youtube-comment-downloader + yt-dlp |
| Web Scraper | trafilatura + feedparser |
| Play Store | google-play-scraper |
| FB Scraper | facebook-scraper |
| TikTok Scraper | TikTokApi + Playwright |

## License

MIT — Free to use, modify, and distribute.
