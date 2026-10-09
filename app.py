#!/usr/bin/env python3
"""Taspen Sentiment Platform - Streamlit entrypoint (design system + sidebar nav).

All logic lives in core.py; pages in pages/. Run:
  ./venv/bin/streamlit run app.py --server.port 9120 --server.address 127.0.0.1
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import core  # noqa: F401  (loads constants + helpers once)

st.set_page_config(page_title="Taspen Sentiment Platform", layout="wide",
                   page_icon="assets/taspen.svg")

# ============================================================== DESIGN SYSTEM
st.markdown("""
<style>
  :root {
    --ss-primary: #005d97;
    --ss-primary-dark: #004a7c;
    --ss-primary-darker: #00304f;
    --ss-primary-light: #e8f1f8;
    --ss-gold: #e8c21d;
    --ss-gold-dark: #d1ae24;
    --ss-ink: #0b1f33;
    --ss-text: #1e3a52;
    --ss-muted: #5c7a94;
    --ss-bg: #eef4f9;
    --ss-surface: #ffffff;
    --ss-border: #d5e2ec;
    --ss-radius: 14px;
    --ss-shadow: 0 1px 2px rgba(11,31,51,.06), 0 4px 14px rgba(11,31,51,.05);
  }

  /* ---------- Streamlit chrome removal ---------- */
  #MainMenu, footer {visibility: hidden;}
  .stApp {background: var(--ss-bg);}
  /* header kept in DOM only so the sidebar expand button stays reachable */
  [data-testid="stHeader"] {background: transparent !important; height: 0 !important;}
  [data-testid="stToolbar"], [data-testid="stAppDeployButton"],
  [data-testid="stMainMenu"], [data-testid="stMainMenuButton"],
  [data-testid="stStatusWidget"] {display: none !important;}
  [data-testid="stDecoration"] {display: none !important;}
  .block-container {padding: 1.1rem 1.4rem 2rem; max-width: 100%;}
  [data-testid="stAppViewContainer"] > .main {padding-top: 0;}

  /* ---------- Sidebar: deep navy with gold spine ---------- */
  [data-testid="stSidebar"] {
    background: linear-gradient(178deg, #00304f 0%, #004a7c 55%, #005d97 100%);
    border-right: 1px solid rgba(255,255,255,.08);
    box-shadow: 6px 0 22px rgba(11,31,51,.14);
  }
  [data-testid="stSidebar"]::after {
    content: ""; position: absolute; top: 0; right: 0; bottom: 0; width: 3px;
    background: linear-gradient(180deg, var(--ss-gold) 0%, rgba(232,194,29,.12) 70%);
  }
  [data-testid="stSidebarHeader"] {padding: .9rem .9rem .3rem; height: auto;}
  [data-testid="stSidebarLogo"] img {max-height: 34px;}
  [data-testid="stSidebarContent"] {padding-top: 0;}
  [data-testid="stSidebarUserContent"] {padding: .3rem .55rem 1rem;}
  /* nav links */
  [data-testid="stSidebarNavItems"] {gap: 2px; padding: 0 .35rem;}
  [data-testid="stSidebarNavLink"] {
    border-radius: 10px; padding: .5rem .7rem; margin: 2px 0;
    color: rgba(255,255,255,.82) !important;
    font-weight: 600; font-size: .86rem;
    transition: background .15s ease, color .15s ease;
  }
  [data-testid="stSidebarNavLink"] span {color: inherit !important;}
  [data-testid="stSidebarNavLink"]:hover {
    background: rgba(255,255,255,.09); color: #fff !important;
  }
  [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: linear-gradient(90deg, rgba(232,194,29,.22) 0%, rgba(232,194,29,.06) 100%);
    color: #fff !important;
    box-shadow: inset 3px 0 0 0 var(--ss-gold);
  }
  /* collapse button (open state) */
  [data-testid="stSidebarCollapseButton"] button {color: rgba(255,255,255,.75) !important;}
  [data-testid="stSidebarCollapseButton"] button:hover {color: #fff !important;}
  /* expand button (collapsed state) - lives in stHeader, must stay visible */
  [data-testid="stExpandSidebarButton"] {
    display: flex !important; position: fixed; top: .55rem; left: .55rem; z-index: 999999;
    background: var(--ss-primary-dark) !important;
    border: 1px solid rgba(255,255,255,.18) !important;
    border-radius: 10px !important; padding: 2px !important;
    box-shadow: 0 3px 12px rgba(11,31,51,.28) !important;
  }
  [data-testid="stExpandSidebarButton"] button,
  [data-testid="stExpandSidebarButton"] svg {
    color: var(--ss-gold) !important;
  }

  /* ---------- Custom components (ui.py) ---------- */
  .tsp-topbar {
    display: flex; align-items: center; justify-content: space-between;
    background: linear-gradient(100deg, #00304f 0%, #004a7c 60%, #0a6ba8 100%);
    border-radius: var(--ss-radius); padding: 14px 22px; margin-bottom: .9rem;
    box-shadow: var(--ss-shadow); position: relative; overflow: hidden;
  }
  .tsp-topbar::after {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 6px;
    background: linear-gradient(180deg, var(--ss-gold), rgba(232,194,29,.35));
  }
  .tsp-topbar-title {color: #fff; font-size: 1.16rem; font-weight: 800; letter-spacing: .2px;}
  .tsp-topbar-desc {color: rgba(255,255,255,.7); font-size: .74rem; margin-top: 3px;}
  .tsp-topbar-brand {text-align: right;}
  .tsp-topbar-sub {color: var(--ss-gold); font-size: .78rem; font-weight: 700;}
  .tsp-topbar-sub2 {color: rgba(255,255,255,.55); font-size: .68rem;}

  .tsp-section {display: flex; align-items: center; gap: 9px; margin: .35rem 0 .55rem;}
  .tsp-step {
    display: inline-flex; align-items: center; justify-content: center;
    width: 22px; height: 22px; border-radius: 50%; flex: 0 0 22px;
    background: var(--ss-primary); color: #fff; font-size: .72rem; font-weight: 700;
  }
  .tsp-section-title {font-size: .95rem; font-weight: 700; color: var(--ss-ink);}
  .tsp-section-desc {font-size: .74rem; color: var(--ss-muted);}

  .tsp-card {
    background: var(--ss-surface); border: 1px solid var(--ss-border);
    border-radius: var(--ss-radius); padding: 14px 16px; box-shadow: var(--ss-shadow);
    margin-bottom: .7rem;
  }
  .tsp-card-head {
    display: flex; align-items: flex-start; gap: 9px;
    padding-bottom: 9px; margin-bottom: 10px;
    border-bottom: 1px solid var(--ss-border); position: relative;
  }
  .tsp-card-head::before {
    content: ""; position: absolute; left: -16px; top: 2px; bottom: 9px; width: 3px;
    background: var(--tsp-accent, var(--ss-primary)); border-radius: 0 3px 3px 0;
  }
  .tsp-card-ic {color: var(--tsp-accent, var(--ss-primary)); display: inline-flex; padding-top: 1px;}
  .tsp-card-title {font-size: .9rem; font-weight: 700; color: var(--ss-ink);}
  .tsp-card-desc {font-size: .72rem; color: var(--ss-muted); margin-top: 1px;}

  .tsp-stats {display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: .7rem;}
  .tsp-stat {
    background: var(--ss-surface); border: 1px solid var(--ss-border);
    border-left: 4px solid var(--tsp-stat, var(--ss-primary));
    border-radius: 12px; padding: 11px 14px; box-shadow: var(--ss-shadow);
  }
  .tsp-stat-top {display: flex; align-items: center; gap: 6px; color: var(--ss-muted);}
  .tsp-stat-label {font-size: .72rem; font-weight: 600; text-transform: uppercase; letter-spacing: .4px;}
  .tsp-stat-value {font-size: 1.5rem; font-weight: 800; color: var(--ss-ink); line-height: 1.25;}
  .tsp-stat-sub {font-size: .7rem; color: var(--ss-muted);}

  .tsp-dot {display: inline-block; border-radius: 50%; vertical-align: middle;}
  .tsp-badge {padding: 2px 8px; border-radius: 6px; font-size: .68rem; font-weight: 700; display: inline-block;}
  .tsp-chip {padding: 2px 9px; border-radius: 999px; font-size: .7rem; font-weight: 600; display: inline-block; margin: 2px 3px 2px 0;}
  .tsp-alerts {display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: .6rem;}
  .tsp-alert {padding: 4px 11px; border-radius: 8px; font-size: .74rem; font-weight: 600; border-width: 1px; border-style: solid;}
  .tsp-alert-danger {background: #fdecec; color: #a12f2f; border-color: #f3c9c9;}
  .tsp-alert-warn {background: #fdf5e6; color: #96631a; border-color: #f0dcb4;}
  .tsp-alert-ok {background: #e9f7f0; color: #16724c; border-color: #c3e7d5;}
  .tsp-alert-info {background: var(--ss-primary-light); color: var(--ss-primary-dark); border-color: #c9dff0;}

  .tsp-kv {display: grid; grid-template-columns: auto 1fr; gap: 5px 14px; font-size: .78rem;}
  .tsp-kv-k {color: var(--ss-muted); font-weight: 600;}
  .tsp-kv-v {color: var(--ss-text);}

  .tsp-sbar {display: flex; height: 12px; border-radius: 999px; overflow: hidden; background: #eef2f6;}
  .tsp-sbar-seg {height: 100%; transition: width .3s ease;}
  .tsp-sbar-legend {font-size: .74rem; color: var(--ss-text); margin-top: 7px; display: flex; gap: 14px; flex-wrap: wrap;}

  .tsp-quote {
    background: #fbfdff; border: 1px solid var(--ss-border);
    border-left: 3px solid var(--tsp-tone, var(--ss-muted));
    border-radius: 10px; padding: 9px 12px; margin-bottom: 7px;
  }
  .tsp-quote-src {font-size: .68rem; font-weight: 700; color: var(--tsp-tone, var(--ss-muted)); text-transform: uppercase; letter-spacing: .4px;}
  .tsp-quote-text {font-size: .8rem; color: var(--ss-text); margin: 3px 0 4px; line-height: 1.4;}
  .tsp-quote-meta {font-size: .68rem; color: var(--ss-muted);}

  .tsp-tile {
    display: flex; align-items: center; gap: 8px;
    background: var(--ss-surface); border: 1px solid var(--ss-border);
    border-top: 3px solid var(--tsp-tile, var(--ss-primary));
    border-radius: 10px; padding: 8px 10px;
  }
  .tsp-tile-ic {color: var(--tsp-tile, var(--ss-primary)); display: inline-flex;}
  .tsp-tile-txt {flex: 1; min-width: 0;}
  .tsp-tile-name {font-size: .78rem; font-weight: 700; color: var(--ss-ink);}
  .tsp-tile-note {font-size: .66rem; color: var(--ss-muted);}
  .tsp-live, .tsp-off {width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex: 0 0 8px;}
  .tsp-live {background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.18);}
  .tsp-off {background: #c3ced8;}

  .tsp-term {background: #0b1620; border-radius: 12px; overflow: hidden; box-shadow: var(--ss-shadow);}
  .tsp-term-bar {display: flex; align-items: center; gap: 6px; padding: 7px 11px; background: #101f2c;}
  .tsp-term-dot {width: 9px; height: 9px; border-radius: 50%; display: inline-block;}
  .tsp-term-title {margin-left: 6px; color: rgba(255,255,255,.6); font-size: .7rem; font-weight: 600;}
  .tsp-term-body {
    margin: 0; padding: 11px 13px; max-height: 300px; overflow: auto;
    color: #9fe8c4; font-size: .72rem; line-height: 1.55;
    font-family: ui-monospace, "JetBrains Mono", Menlo, monospace; white-space: pre-wrap;
  }

  .tsp-prog {height: 7px; background: #e6eef5; border-radius: 999px; overflow: hidden;}
  .tsp-prog-fill {height: 100%; background: linear-gradient(90deg, var(--ss-primary), #2b8ec7);}
  .tsp-prog-label {font-size: .7rem; color: var(--ss-muted); margin-top: 4px;}

  .tsp-plotcard {
    background: var(--ss-surface); border-radius: var(--ss-radius);
    box-shadow: var(--ss-shadow); padding: 4px 2px 2px;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--ss-surface); border-radius: var(--ss-radius);
    box-shadow: var(--ss-shadow); padding: 12px 16px;
  }

  .tsp-aiintro {font-size: .8rem; color: var(--ss-text); padding-top: 10px;}
  .tsp-md {font-size: .8rem; line-height: 1.55; color: var(--ss-text);}
  .tsp-md h1, .tsp-md h2, .tsp-md h3 {font-size: .9rem;}
  .tsp-md li {margin-bottom: 2px;}
  .tsp-md p {margin: 4px 0;}
  .tsp-md table {font-size: .76rem;}

  .tsp-chat-row {display: flex; margin: 6px 0;}
  .tsp-chat-user {
    margin-left: auto; max-width: 72%;
    background: linear-gradient(96deg, var(--ss-primary-dark), var(--ss-primary));
    color: #fff; border-radius: 14px 14px 4px 14px; padding: 9px 14px;
    font-size: .8rem; line-height: 1.45; box-shadow: 0 2px 8px rgba(0,74,124,.18);
  }
  .tsp-chat-ai {
    max-width: 86%; background: var(--ss-surface);
    border: 1px solid var(--ss-border); border-radius: 14px 14px 14px 4px;
    padding: 10px 14px; box-shadow: var(--ss-shadow);
  }
  .tsp-chat-ai-head {
    display: flex; align-items: center; gap: 5px;
    font-size: .66rem; font-weight: 700; letter-spacing: .4px;
    text-transform: uppercase; color: var(--ss-primary); margin-bottom: 4px;
  }

  .tsp-insight {font-size: .78rem; color: var(--ss-text); padding: 4px 0 4px 2px; line-height: 1.4;}
  .tsp-insight b {color: var(--ss-ink);}
  .tsp-insight svg {vertical-align: -2px;}
  .tsp-empty {
    text-align: center; padding: 34px 18px; color: var(--ss-muted);
    background: var(--ss-surface); border: 1px dashed var(--ss-border); border-radius: var(--ss-radius);
  }
  .tsp-empty-title {font-size: .92rem; font-weight: 700; color: var(--ss-text); margin-top: 8px;}
  .tsp-empty-desc {font-size: .76rem; margin-top: 3px;}

  /* ---------- Restyle the few native widgets we keep ---------- */
  h1, h2, h3, h4 {color: var(--ss-ink);}
  h1 {font-size: 1.35rem;} h2 {font-size: 1.12rem;} h3 {font-size: 1rem;} h4 {font-size: .9rem;}
  p, li {font-size: .82rem; line-height: 1.4; color: var(--ss-text);}
  [data-testid="stCaptionContainer"] p, .stCaption {font-size: .72rem; color: var(--ss-muted);}
  [data-testid="stWidgetLabel"] p {font-size: .76rem; font-weight: 600; color: var(--ss-text);}

  [data-baseweb="input"], [data-baseweb="base-input"],
  [data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"],
  [data-testid="stTextAreaRootElement"] {
    background: var(--ss-surface) !important; border-radius: 9px !important;
    border-color: var(--ss-border) !important;
  }
  [data-baseweb="input"]:focus-within, [data-testid="stTextInputRootElement"]:focus-within {
    border-color: var(--ss-primary) !important; box-shadow: 0 0 0 3px rgba(0,93,151,.12) !important;
  }
  input, textarea {color: var(--ss-text) !important; font-size: .82rem !important;}
  [data-baseweb="select"] > div {
    background: var(--ss-surface) !important; border-radius: 9px !important;
    border-color: var(--ss-border) !important; font-size: .82rem;
  }
  [data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {
    background: var(--ss-primary-light) !important; color: var(--ss-primary-dark) !important;
  }

  [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
    border-radius: 9px; border: 1px solid var(--ss-border);
    background: var(--ss-surface); color: var(--ss-primary-dark);
    font-size: .8rem; font-weight: 600; padding: .38rem .9rem;
    transition: background .15s ease, border-color .15s ease, transform .06s ease;
  }
  [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
    border-color: var(--ss-primary); background: var(--ss-primary-light);
  }
  [data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(96deg, var(--ss-primary-dark), var(--ss-primary));
    border-color: var(--ss-primary-dark); color: #fff;
    box-shadow: 0 2px 8px rgba(0,74,124,.24);
  }
  [data-testid="stButton"] button[kind="primary"]:hover {
    background: linear-gradient(96deg, var(--ss-primary-darker), var(--ss-primary-dark));
    transform: translateY(-1px);
  }
  [data-testid="stBaseButton-pills"] {
    border-radius: 999px !important; font-size: .74rem !important;
    border: 1px solid var(--ss-border) !important; background: var(--ss-surface) !important;
    color: var(--ss-primary-dark) !important;
  }
  [data-testid="stBaseButton-pills"][aria-checked="true"] {
    background: var(--ss-primary) !important; color: #fff !important;
    border-color: var(--ss-primary) !important;
  }

  [data-testid="stProgress"] > div > div {background: linear-gradient(90deg, var(--ss-primary), #2b8ec7);}
  div[data-testid="stExpander"] details {
    border-radius: var(--ss-radius); border: 1px solid var(--ss-border);
    background: var(--ss-surface); box-shadow: var(--ss-shadow); overflow: hidden;
  }
  div[data-testid="stExpander"] details summary {font-size: .82rem; font-weight: 600; color: var(--ss-text);}
  div[data-testid="stExpander"] details summary:hover {color: var(--ss-primary);}
  [data-testid="stDataFrame"] {border-radius: 10px; overflow: hidden; border: 1px solid var(--ss-border);}
  [data-testid="stAlertContainer"] {border-radius: 10px; font-size: .8rem;}
  [data-testid="stChatMessage"] {
    border-radius: 12px; padding: 8px 12px; background: var(--ss-surface);
    border: 1px solid var(--ss-border); box-shadow: var(--ss-shadow);
  }
  [data-testid="stChatInput"] textarea {font-size: .82rem;}
  [data-testid="stSpinner"] {color: var(--ss-primary);}
</style>
""", unsafe_allow_html=True)

# ================================================================ SIDEBAR NAV
from pages.p_scrape import page_scrape          # noqa: E402
from pages.p_dashboard import page_dashboard    # noqa: E402
from pages.p_ai import page_ai                  # noqa: E402

page = st.navigation([
    st.Page(page_scrape,    title="Scrape & Analisis", icon=":material/radar:"),
    st.Page(page_dashboard, title="Dashboard",         icon=":material/insights:"),
    st.Page(page_ai,        title="AI Insight",        icon=":material/auto_awesome:"),
], position="sidebar")

st.logo("assets/taspen.svg")

page.run()
