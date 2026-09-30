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
- **AI Chatbot** — Ask questions about the data
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

### Step 2: Install Playwright (for TikTok scraper)

```bash
playwright install chromium
```

### Step 3: Download Fonts

The app uses DejaVuSans fonts for PDF export and wordclouds:

```bash
mkdir -p assets/fonts
# On Debian/Ubuntu:
cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf assets/fonts/
cp /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf assets/fonts/
# Or download from: https://dejavu-fonts.github.io/
```

### Step 4: Configure Environment

```bash
cp .env.example .env
nano .env
```

Set these variables:
- `LLM_BASE_URL` — Your LLM API endpoint (OpenAI, Ollama, vLLM, etc.)
- `LLM_MODEL` — Model name (e.g., `gpt-3.5-turbo`, `llama3`, etc.)
- `LLM_API_KEY` — API key (leave empty for local models like Ollama)
- `SENTIMENT_MODEL` — HuggingFace model (default: Indonesian Roberta)
- `APP_TITLE` — Your app title
- `APP_SUBTITLE` — Subtitle shown under title

### Step 5: Run

```bash
./venv/bin/streamlit run app.py --server.port 9120 --server.address 127.0.0.1 --server.headless true
```

### Step 6: Nginx Reverse Proxy (Production)

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
    }
}
```

### Step 7: Systemd Service (Auto-start)

```ini
# /etc/systemd/system/sentiment-analysis.service
[Unit]
Description=Sentiment Analysis App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/sentiment-analysis
ExecStart=/opt/sentiment-analysis/venv/bin/streamlit run app.py --server.port 9120 --server.address 127.0.0.1 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable sentiment-analysis
systemctl start sentiment-analysis
```

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

9. **Chat with AI** — Ask follow-up questions about the data in the AI panel

## Security Notes

- **Credentials are stored locally** in `sessions/` directory as JSON files. They never leave your server.
- **LLM API key** is read from environment variables or `.env` file. Never commit `.env` to git.
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

Add your app IDs to `.env`:

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
| YT Scraper | youtube-comment-downloader |
| Web Scraper | trafilatura + feedparser |
| Play Store | google-play-scraper |
| FB Scraper | facebook-scraper |
| TikTok Scraper | TikTokApi + Playwright |

## License

MIT — Free to use, modify, and distribute.
