#!/usr/bin/env python3
"""Configuration for Sentiment Analysis app.

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

# === Play Store apps to scrape (configurable) ===
# Format: {"App Name": "com.app.id"}
PLAYSTORE_APPS = {
    "Daily TASPEN": os.environ.get("PLAYSTORE_APP_1", ""),
    "my taspen LIFE": os.environ.get("PLAYSTORE_APP_2", ""),
    "New Taspen Easy": os.environ.get("PLAYSTORE_APP_3", ""),
    "Taspen Easy": os.environ.get("PLAYSTORE_APP_4", ""),
    "PAOS": os.environ.get("PLAYSTORE_APP_5", ""),
}
# Remove empty entries
PLAYSTORE_APPS = {k: v for k, v in PLAYSTORE_APPS.items() if v}

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
