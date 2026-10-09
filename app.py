#!/usr/bin/env python3
"""Taspen Sentiment Platform - Streamlit entrypoint (theme + sidebar navigation).

Semua logic di core.py; halaman di pages/. Jalankan:
  ./venv/bin/streamlit run app.py --server.port 9120 --server.address 127.0.0.1
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import core  # noqa: F401  (muat constants/helper sekali di sini)

st.set_page_config(page_title="Taspen Sentiment Platform", layout="wide",
                   page_icon="assets/taspen.svg")

# === Taspen brand theme ===
st.markdown("""
<style>
  :root {
    --ss-primary: #005d97;
    --ss-primary-dark: #004a7c;
    --ss-primary-light: #e8f1f8;
    --ss-gold: #e8c21d;
    --ss-gold-dark: #d1ae24;
    --ss-ink: #0b1f33;
    --ss-text: #1e3a52;
    --ss-muted: #5c7a94;
    --ss-bg: #f4f8fb;
    --ss-surface: #ffffff;
    --ss-border: #d5e2ec;
    --ss-radius: 14px;
    --ss-success: #1e9e6a;
    --ss-warning: #e8a13a;
    --ss-danger: #d64545;
    --ss-positif: #1e9e6a;
    --ss-netral: #8aa5b5;
    --ss-negatif: #d64545;
  }
  [data-testid="stHeader"] {display: none;}
  #MainMenu, footer {visibility: hidden;}
  .stApp {background: var(--ss-bg);}
  .block-container {padding-top: 0.5rem; padding-bottom: 1rem; max-width: 100%;}

  /* Custom topbar (per page) */
  .tsp-topbar {
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(90deg, var(--ss-primary-dark) 0%, var(--ss-primary) 75%);
    border-radius: var(--ss-radius); padding: 12px 20px; margin-bottom: 0.8rem;
    border-left: 6px solid var(--ss-gold);
  }
  .tsp-topbar-title {color: #fff; font-size: 1.15rem; font-weight: 800;}
  .tsp-topbar-desc {color: rgba(255,255,255,0.75); font-size: 0.74rem; margin-top: 2px;}
  .tsp-topbar-brand {text-align: right;}
  .tsp-topbar-sub {color: var(--ss-gold); font-size: 0.78rem; font-weight: 700;}
  .tsp-topbar-sub2 {color: rgba(255,255,255,0.6); font-size: 0.68rem;}
  /* Sidebar nav */
  [data-testid="stSidebar"] {
      background: var(--ss-primary-dark);
  }
  [data-testid="stSidebar"] * {color: rgba(255,255,255,0.85) !important;}
  [data-testid="stSidebarNav"] {display: none;}
  [data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top: 1rem;}
  /* nav item hover/selected */
  [data-testid="stSidebar"] [data-testid="stNavLink"] {border-radius: 10px; margin: 2px 8px;}
  [data-testid="stSidebar"] [data-testid="stNavLink"]:hover {background: rgba(255,255,255,0.08);}
  [data-testid="stSidebar"] [data-testid="stNavLink"][aria-current="page"] {
      background: rgba(232,194,29,0.18);
      border-left: 3px solid var(--ss-gold);
  }
  /* collapse control visible */
  [data-testid="stSidebarCollapsedControl"] {background: var(--ss-primary-dark);}
  /* hide default header completely */
  [data-testid="stHeader"] {display: none !important; height: 0 !important;}
  .stApp > header {display: none;}

  [data-testid="stMetric"] {
      background: var(--ss-surface);
      border: 1px solid var(--ss-border);
      border-top: 3px solid var(--ss-gold);
      border-radius: var(--ss-radius);
      padding: 8px 10px !important;
  }
  [data-testid="stMetricLabel"] p {font-size: 0.72rem; opacity: 0.8; margin-bottom: 0; color: var(--ss-text);}
  [data-testid="stMetricValue"] {font-size: 1.1rem; color: var(--ss-primary-dark);}
  [data-testid="stMetricDelta"] {font-size: 0.7rem;}
  div[data-testid="stExpander"] details {border-radius: var(--ss-radius); border-color: var(--ss-border); background: var(--ss-surface);}
  [data-testid="stChatMessage"] {border-radius: 8px; padding: 4px 8px;}
  .stTabs [data-baseweb="tab-list"] {gap: 4px;}
  .stTabs [data-baseweb="tab"] {
      padding: 4px 10px; font-size: 0.85rem; border-radius: 8px;
      color: var(--ss-muted); font-weight: 600;
  }
  .stTabs [data-baseweb="tab"][aria-selected="true"] {
      color: var(--ss-primary-dark); background: var(--ss-primary-light);
  }
  h1, h2, h3, h4 {color: var(--ss-ink);}
  h1 {font-size: 1.4rem; margin-bottom: 0.2rem;}
  h2 {font-size: 1.15rem; margin-bottom: 0.15rem;}
  h3 {font-size: 1rem; margin-bottom: 0.1rem;}
  h4 {font-size: 0.88rem; margin-bottom: 0.1rem;}
  p, li {font-size: 0.82rem; line-height: 1.35; color: var(--ss-text);}
  .stCaption {font-size: 0.72rem; color: var(--ss-muted);}
  [data-testid="stTextInput"], [data-testid="stNumberInput"] {margin-bottom: 0.2rem;}
  .stSlider > div {padding-top: 0; padding-bottom: 0;}
  [data-testid="stButton"] button {
      padding: 4px 12px; font-size: 0.82rem;
      border: 1px solid var(--ss-border); border-radius: 8px; background: var(--ss-surface);
  }
  [data-testid="stButton"] button[kind="primary"] {
      background: var(--ss-primary); border-color: var(--ss-primary); color: #fff;
  }
  [data-testid="stButton"] button[kind="primary"]:hover {background: var(--ss-primary-dark);}
  /* Sticky right column */
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stChatMessage"]),
  .sticky-right {position: sticky; top: 0;}
  .ss-card-title {font-size: 0.88rem; font-weight: 700; color: var(--ss-ink); margin-bottom: 0.1rem;}
  .ss-card-desc {font-size: 0.72rem; color: var(--ss-muted); margin-bottom: 0.3rem;}
  div[data-testid="stExpander"] details summary {font-size: 0.85rem;}
</style>
""", unsafe_allow_html=True)

# ================================================================ SIDEBAR NAVIGATION
# ================================================================ SIDEBAR PAGES
from pages.p_scrape import page_scrape
from pages.p_dashboard import page_dashboard
from pages.p_ai import page_ai

page = st.navigation([
    st.Page(page_scrape,    title="Scrape & Analisis", icon=":material/rocket_launch:"),
    st.Page(page_dashboard, title="Dashboard",         icon=":material/dashboard:"),
    st.Page(page_ai,        title="AI Insight",        icon=":material/auto_awesome:"),
], position="sidebar")

st.logo("assets/taspen.svg")

page.run()

