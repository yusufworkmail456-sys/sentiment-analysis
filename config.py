#!/usr/bin/env python3
"""Configuration for Sentimetter - multi-platform sentiment analysis.

All sensitive/environment-specific values are read from environment variables.
Copy .env.example to .env and fill in your values.
"""
import os
from pathlib import Path

# === Paths ===
BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)
OUT_DIR = BASE_DIR / "hasil"
OUT_DIR.mkdir(exist_ok=True)
FONT_DIR = BASE_DIR / "assets" / "fonts"
FONT_REGULAR = str(FONT_DIR / "DejaVuSans.ttf")
FONT_BOLD = str(FONT_DIR / "DejaVuSans-Bold.ttf")

# === LLM (OpenAI-compatible API) ===
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")

# === Sentiment Model ===
MODEL_NAME = os.environ.get(
    "SENTIMENT_MODEL",
    "w11wo/indonesian-roberta-base-sentiment-classifier"
)

# === Proxy (for Instagram scraper) ===
IG_PROXY = os.environ.get("IG_PROXY", "")

# === App Branding ===
APP_TITLE = os.environ.get("APP_TITLE", "Sentiment Analysis")
APP_SUBTITLE = os.environ.get("APP_SUBTITLE",
    "Multi-platform · IndoBERT · AI insight")
APP_VERSION = os.environ.get("APP_VERSION", "2.1.0")

# === Scheduled scraping (historical data) ===
SCHEDULE_ENABLED = os.environ.get("SCHEDULE_ENABLED", "1")
SCHEDULE_KEYWORDS = os.environ.get("SCHEDULE_KEYWORDS", "taspen")
SCHEDULE_INTERVAL_HOURS = os.environ.get("SCHEDULE_INTERVAL_HOURS", "6")

# === Play Store apps to scrape (configurable) ===
# Format: {env var name: display fallback}
# Set PLAYSTORE_APP_1..N in .env with your app package IDs
PLAYSTORE_APPS = {
    os.environ.get("PLAYSTORE_APP_1", ""): os.environ.get("PLAYSTORE_APP_1", ""),
    os.environ.get("PLAYSTORE_APP_2", ""): os.environ.get("PLAYSTORE_APP_2", ""),
    os.environ.get("PLAYSTORE_APP_3", ""): os.environ.get("PLAYSTORE_APP_3", ""),
    os.environ.get("PLAYSTORE_APP_4", ""): os.environ.get("PLAYSTORE_APP_4", ""),
    os.environ.get("PLAYSTORE_APP_5", ""): os.environ.get("PLAYSTORE_APP_5", ""),
}
# Remove empty entries
PLAYSTORE_APPS = {k: v for k, v in PLAYSTORE_APPS.items() if k}

def load_env():
    """Load .env file if it exists."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

# Load on import
load_env()
# Re-read after load
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL_NAME = os.environ.get("SENTIMENT_MODEL", "w11wo/indonesian-roberta-base-sentiment-classifier")
IG_PROXY = os.environ.get("IG_PROXY", "")
APP_TITLE = os.environ.get("APP_TITLE", "Sentiment Analysis")
APP_SUBTITLE = os.environ.get("APP_SUBTITLE", "Multi-platform · IndoBERT · AI insight")
