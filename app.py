#!/usr/bin/env python3
"""Taspen Sentiment Platform - Streamlit entrypoint."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import core  # noqa: F401
import ui

st.set_page_config(
    page_title="Taspen Sentiment Platform",
    layout="wide",
    page_icon="assets/taspen.svg",
)

# ── Self-hosted fonts fallback ────────────────────────────────────────────
import pathlib as _pl
_fdir = _pl.Path(__file__).parent / "assets" / "fonts"
_fontcss = ""
if (_fdir / "fonts.css").exists():
    _fontcss = (_fdir / "fonts.css").read_text()
st.markdown(f"""
<style>
  {_fontcss}
  @font-face {{
    font-family:'Material Symbols Outlined'; font-style:normal; font-weight:400;
    src:url('assets/fonts/MaterialSymbolsOutlined.woff2') format('woff2');
    font-display:block;
  }}
</style>
""", unsafe_allow_html=True)

# ── Global CSS Design System ──────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
<style>
/* ── Design Tokens ─────────────────────────────────────────────── */
:root {
  --navy:        #004a7c;
  --navy-dark:   #003a61;
  --navy-light:  #0064a8;
  --blue:        #005d97;
  --blue-soft:   #e3edf6;
  --gold:        #c8a200;
  --gold-dark:   #a88a00;
  --gold-soft:   #fdf6d8;
  --ink:         #0d1f2e;
  --text:        #2d3f50;
  --muted:       #7a93a8;
  --line:        #dde6f0;
  --bg:          #f4f7fb;
  --surface:     #ffffff;
  --tint:        #f0f4f9;
  --pos:         #0c7a55;
  --pos-soft:    #d8f2ea;
  --neu:         #7a93a8;
  --neg:         #bf2d2d;
  --neg-soft:    #fae0e0;
  --gold-t:      #fdf6d8;
  --warn:        #d97706;
  --shadow:      0 1px 8px rgba(13,31,46,.06);
  --shadow-md:   0 4px 16px rgba(13,31,46,.10);
  --radius:      14px;
  --radius-sm:   10px;
}

/* ── Base reset ─────────────────────────────────────────────────── */
@layer base {
  html,body { margin:0; padding:0; }
  body { overscroll-behavior:none; }
}
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--line); border-radius:99px; }

/* ── Streamlit chrome removal ────────────────────────────────────── */
#MainMenu, footer { visibility:hidden; }
.stApp { background:var(--bg); }
[data-testid="stHeader"] { background:transparent !important; height:0 !important; min-height:0 !important; }
[data-testid="stToolbar"], [data-testid="stAppDeployButton"],
[data-testid="stMainMenu"], [data-testid="stMainMenuButton"],
[data-testid="stStatusWidget"], [data-testid="stDecoration"] { display:none !important; }
.block-container { padding:0 24px 48px; max-width:100%; }
[data-testid="stAppViewContainer"] > .main { padding-top:0; }

/* ── Sidebar ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background:var(--surface) !important;
  border-right:1px solid var(--line) !important;
  box-shadow:4px 0 18px rgba(13,31,46,.04) !important;
}
[data-testid="stSidebarHeader"] { padding:14px 20px 4px; min-height:64px; }
[data-testid="stSidebarContent"] { padding-top:0; }
[data-testid="stSidebarUserContent"] { padding:8px 14px 16px; }
[data-testid="stSidebarNavItems"] { gap:2px; padding:0 14px; }
[data-testid="stSidebarNavLink"] {
  border-radius:var(--radius-sm); padding:9px 12px; margin:1px 0;
  color:var(--text) !important; font-weight:600; font-size:.86rem;
  transition:background .15s, color .15s;
}
[data-testid="stSidebarNavLink"]:hover { background:var(--tint); color:var(--ink) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background:var(--navy); color:#fff !important;
  box-shadow:0 2px 10px rgba(0,74,124,.28);
}
[data-testid="stSidebarNavLink"] span { color:inherit !important; }
[data-testid="stSidebarCollapseButton"] button { color:var(--muted) !important; }
[data-testid="stExpandSidebarButton"] {
  display:flex !important; position:fixed; top:12px; left:12px; z-index:999999;
  background:var(--surface) !important; border:1px solid var(--line) !important;
  border-radius:var(--radius-sm) !important; padding:3px !important;
  box-shadow:var(--shadow) !important;
}
[data-testid="stExpandSidebarButton"] button,
[data-testid="stExpandSidebarButton"] svg { color:var(--navy) !important; }

/* ── Topbar ──────────────────────────────────────────────────────── */
.tsp-topbar {
  position:sticky; top:0; z-index:40;
  display:flex; align-items:center; justify-content:space-between; gap:16px;
  background:rgba(255,255,255,.94); backdrop-filter:blur(12px);
  border-bottom:1px solid var(--line);
  padding:0 24px; height:62px; margin:0 -24px 4px;
  box-shadow:0 1px 6px rgba(13,31,46,.05);
}
.tsp-topbar-left { display:flex; flex-direction:column; gap:2px; }
.tsp-topbar-title { color:var(--ink); font-size:1.02rem; font-weight:800; letter-spacing:-.01em; line-height:1.2; }
.tsp-topbar-desc { color:var(--muted); font-size:.74rem; }
.tsp-topbar-brand { display:flex; flex-direction:column; align-items:flex-end; gap:4px; }
.tsp-topbar-logos { display:flex; align-items:center; gap:10px; }
.tsp-topbar-divider { width:1px; height:22px; background:var(--line); }
.tsp-topbar-app-name { font-size:.7rem; font-weight:700; color:var(--navy); letter-spacing:.02em; text-align:right; }

/* ── Sidebar status & footer ─────────────────────────────────────── */
.tsp-status {
  display:flex; align-items:center; justify-content:space-between;
  background:var(--tint); border-radius:var(--radius-sm);
  padding:8px 12px; margin:0 16px 8px; font-size:.74rem;
}
.tsp-status-l { display:flex; align-items:center; gap:7px; color:var(--ink); font-weight:600; }
.tsp-status-r { color:var(--muted); font-size:.68rem; }
.tsp-dot-ok { width:8px; height:8px; border-radius:50%; background:var(--pos); animation:tsp-pulse 2s infinite; flex:0 0 8px; }
@keyframes tsp-pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
.tsp-sb-label { font-size:.63rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:6px 20px 4px; }
.tsp-sb-foot { background:var(--tint); border-radius:var(--radius-sm); padding:11px 13px; margin:8px 16px 0; }
.tsp-sb-foot-row { display:flex; align-items:center; justify-content:space-between; font-size:.72rem; color:var(--ink); font-weight:600; }
.tsp-sb-foot-sub { display:flex; align-items:center; justify-content:space-between; font-size:.66rem; color:var(--muted); margin-top:6px; }
.tsp-gold-text { color:var(--gold-dark); font-weight:700; }
.tsp-meter { height:5px; border-radius:999px; background:var(--line); overflow:hidden; margin:6px 0; }
.tsp-meter > div { height:100%; border-radius:999px; background:var(--navy); }

/* ── Typography ──────────────────────────────────────────────────── */
body,.stApp,p,li,div,button,input,textarea,label,th,td {
  font-family:'Plus Jakarta Sans',system-ui,sans-serif !important; color:var(--text);
}
span:not(.material-symbols-outlined) { font-family:'Plus Jakarta Sans',system-ui,sans-serif !important; }
.material-symbols-outlined { font-family:'Material Symbols Outlined' !important; color:inherit; }
h1,h2,h3,h4 { color:var(--ink); font-family:'Plus Jakarta Sans',sans-serif !important; }
h1 { font-size:1.45rem; font-weight:800; letter-spacing:-.02em; }
h2 { font-size:1.15rem; font-weight:700; }
h3 { font-size:1rem; font-weight:700; }
p,li { font-size:.85rem; line-height:1.55; }
.tsp-mono,code,pre { font-family:'JetBrains Mono',monospace !important; }
[data-testid="stCaptionContainer"] p { font-size:.74rem; color:var(--muted); }
[data-testid="stWidgetLabel"] p { font-size:.76rem; font-weight:600; color:var(--text); }

/* ── Page head block ─────────────────────────────────────────────── */
.tsp-phead {
  display:flex; align-items:flex-end; justify-content:space-between;
  gap:16px; flex-wrap:wrap;
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); padding:18px 22px;
  margin-bottom:16px; box-shadow:var(--shadow);
}
.tsp-phead-chips { display:flex; gap:6px; margin-bottom:6px; flex-wrap:wrap; }
.tsp-chip {
  display:inline-flex; align-items:center; gap:4px;
  padding:3px 10px; border-radius:999px;
  font-size:.7rem; font-weight:700;
}
.tsp-h1 { font-size:1.4rem; font-weight:800; letter-spacing:-.02em; margin:0; color:var(--ink); }
.tsp-phead-desc { font-size:.82rem; color:var(--muted); margin:4px 0 0; max-width:700px; }
.tsp-phead-actions { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.tsp-btn {
  display:inline-flex; align-items:center; gap:6px;
  padding:7px 14px; border-radius:var(--radius-sm);
  font-size:.78rem; font-weight:700; cursor:pointer;
}
.tsp-btn-primary { background:var(--navy); color:#fff; box-shadow:0 2px 8px rgba(0,74,124,.25); }
.tsp-btn-secondary { background:var(--surface); color:var(--navy); border:1px solid var(--line); }
.tsp-btn-gold { background:var(--gold-soft); color:var(--gold-dark); border:1px solid #e8d78a; }

/* ── KPI cards ───────────────────────────────────────────────────── */
.tsp-kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(175px,1fr)); gap:12px; margin-bottom:16px; }
.tsp-kpi {
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); padding:16px 18px;
  box-shadow:var(--shadow); position:relative; overflow:hidden;
  transition:box-shadow .2s;
}
.tsp-kpi:hover { box-shadow:var(--shadow-md); }
.tsp-kpi-top { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.tsp-kpi-label { font-size:.67rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.tsp-kpi-ic { width:32px; height:32px; border-radius:9px; display:inline-flex; align-items:center; justify-content:center; flex:0 0 32px; }
.tsp-kpi-value { font-size:1.65rem; font-weight:700; letter-spacing:-.03em; line-height:1.25; margin-top:8px; }
.tsp-kpi-sub { font-size:.72rem; color:var(--muted); margin-top:3px; }
.tsp-spark { width:100%; height:28px; margin-top:10px; }

/* ── Cards ───────────────────────────────────────────────────────── */
.tsp-card {
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); padding:18px 20px;
  box-shadow:var(--shadow); margin-bottom:12px;
}
.tsp-card-top { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:10px; }
.tsp-card-title { font-size:.92rem; font-weight:700; color:var(--ink); display:flex; align-items:center; gap:7px; }
.tsp-card-desc { font-size:.74rem; color:var(--muted); margin:2px 0 0; }
.tsp-section-head { display:flex; align-items:center; gap:6px; padding:4px 0 10px; }

/* ── Donut chart ─────────────────────────────────────────────────── */
.tsp-donut { display:flex; align-items:center; gap:20px; justify-content:center; padding:8px 0; flex-wrap:wrap; }
.tsp-donut-ring { width:168px; height:168px; border-radius:50%; position:relative; flex:0 0 168px; }
.tsp-donut-hole {
  position:absolute; inset:28px; background:var(--surface);
  border-radius:50%; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:2px;
  box-shadow:inset 0 0 0 1px var(--line);
}
.tsp-donut-lab { font-size:.63rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.tsp-donut-val { font-size:1.55rem; font-weight:700; color:var(--ink); letter-spacing:-.03em; }
.tsp-donut-leg { display:flex; flex-direction:column; gap:8px; min-width:145px; }
.tsp-lg-leg { display:flex; align-items:center; justify-content:space-between; gap:12px; background:var(--tint); border-radius:9px; padding:7px 11px; }
.tsp-lg-k { display:flex; align-items:center; gap:6px; font-size:.74rem; font-weight:700; }
.tsp-lg-v { font-size:.82rem; font-weight:700; color:var(--ink); }

/* ── Sentiment stacked bar ───────────────────────────────────────── */
.tsp-sbar { display:flex; height:10px; border-radius:999px; overflow:hidden; background:var(--tint); }
.tsp-sbar > div { height:100%; }
.tsp-sbar-lg { display:flex; gap:14px; flex-wrap:wrap; margin-top:8px; }
.tsp-lg { display:flex; align-items:center; gap:5px; font-size:.75rem; }
.tsp-dot { display:inline-block; border-radius:50%; flex:0 0 auto; }
.tsp-prog { height:6px; border-radius:999px; background:var(--tint); overflow:hidden; margin:7px 0 5px; }
.tsp-prog > div { height:100%; border-radius:999px; background:var(--navy); }
.tsp-prog-label { font-size:.7rem; color:var(--muted); }

/* ── Per-source card ─────────────────────────────────────────────── */
.tsp-src-card {
  background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius); padding:14px 16px;
  box-shadow:var(--shadow);
}
.tsp-src-head { display:flex; align-items:center; gap:10px; margin-bottom:4px; }
.tsp-src-ic { flex:0 0 auto; }
.tsp-src-name { font-size:.88rem; font-weight:700; color:var(--ink); line-height:1.2; }
.tsp-src-vol { font-size:.7rem; color:var(--muted); }
.tsp-badge-gss { margin-left:auto; font-size:.7rem; font-weight:700; padding:3px 8px; border-radius:999px; }
.tsp-src-legend { display:flex; gap:10px; flex-wrap:wrap; margin-top:6px; }
.tsp-src-lg { display:flex; align-items:center; gap:5px; font-size:.71rem; color:var(--text); }

/* ── Badges & tokens ─────────────────────────────────────────────── */
.tsp-badge { display:inline-flex; align-items:center; gap:4px; padding:3px 10px; border-radius:999px; font-size:.72rem; font-weight:700; }
.tsp-tok { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius:999px; font-size:.72rem; font-weight:600; margin:3px 5px 3px 0; }
.tsp-tok-sc { background:rgba(255,255,255,.75); border-radius:6px; padding:1px 6px; font-size:.68rem; font-weight:700; }
.tsp-alerts { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:10px; }
.tsp-alert { padding:4px 12px; border-radius:9px; font-size:.74rem; font-weight:700; border:1px solid transparent; }
.tsp-alert-neg { background:var(--neg-soft); color:var(--neg); border-color:#f3c6c6; }
.tsp-alert-warn { background:#fef3c7; color:var(--warn); border-color:#f0dcb4; }
.tsp-alert-ok  { background:var(--pos-soft); color:var(--pos); border-color:#c3e7d5; }
.tsp-alert-info { background:var(--blue-soft); color:var(--navy); border-color:#c9dff0; }

/* ── Insight bullets & quotes ────────────────────────────────────── */
.tsp-ins-wrap { display:flex; flex-direction:column; gap:2px; }
.tsp-ins { display:flex; align-items:flex-start; gap:6px; font-size:.79rem; padding:4px 0; line-height:1.5; }
.tsp-ins .material-symbols-outlined { flex:0 0 auto; margin-top:2px; }
.tsp-quote { background:var(--tint); border:1px solid var(--line); border-left:3px solid var(--muted); border-radius:var(--radius-sm); padding:9px 12px; margin-bottom:7px; }
.tsp-quote-src  { font-size:.66rem; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.tsp-quote-text { font-size:.8rem; color:var(--ink); margin:3px 0 4px; line-height:1.45; }
.tsp-quote-meta { font-size:.68rem; color:var(--muted); }

/* ── AI / chat ───────────────────────────────────────────────────── */
.tsp-chat-row { display:flex; margin:6px 0; }
.tsp-chat-user { margin-left:auto; max-width:72%; background:var(--navy); color:#fff; border-radius:14px 14px 4px 14px; padding:9px 14px; font-size:.8rem; line-height:1.45; box-shadow:0 2px 8px rgba(0,74,124,.18); }
.tsp-chat-ai { max-width:86%; background:var(--surface); border:1px solid var(--line); border-radius:14px 14px 14px 4px; padding:10px 14px; box-shadow:var(--shadow); }
.tsp-chat-ai-head { display:flex; align-items:center; gap:5px; font-size:.64rem; font-weight:800; letter-spacing:.05em; text-transform:uppercase; color:var(--navy); margin-bottom:4px; }
.tsp-md { font-size:.82rem; line-height:1.6; color:var(--text); }
.tsp-md h1,.tsp-md h2,.tsp-md h3 { font-size:.92rem; }
.tsp-md table { font-size:.76rem; }
.tsp-kv { display:grid; grid-template-columns:auto 1fr; gap:5px 14px; font-size:.78rem; }
.tsp-kv-k { color:var(--muted); font-weight:600; }
.tsp-kv-v { color:var(--text); }

/* ── Terminal ─────────────────────────────────────────────────────── */
.tsp-term { background:#0b1820; border-radius:var(--radius); overflow:hidden; box-shadow:var(--shadow); }
.tsp-term-bar { display:flex; align-items:center; gap:6px; padding:7px 11px; background:#101f2c; }
.tsp-term-dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
.tsp-term-title { margin-left:6px; color:rgba(255,255,255,.5); font-size:.7rem; font-weight:600; }
.tsp-term-body { margin:0; padding:11px 13px; max-height:280px; overflow:auto; color:#9fe8c4; font-size:.72rem; line-height:1.55; font-family:'JetBrains Mono',monospace; white-space:pre-wrap; }

/* ── Source tile / live dot ──────────────────────────────────────── */
.tsp-tile { display:flex; align-items:center; gap:9px; background:var(--surface); border:1px solid var(--line); border-radius:11px; padding:9px 11px; }
.tsp-tile-ic { display:inline-flex; }
.tsp-tile-txt { flex:1; min-width:0; }
.tsp-tile-name { font-size:.78rem; font-weight:700; color:var(--ink); }
.tsp-tile-note { font-size:.65rem; color:var(--muted); }
.tsp-live,.tsp-off { width:8px; height:8px; border-radius:50%; display:inline-block; flex:0 0 8px; }
.tsp-live { background:var(--pos); box-shadow:0 0 0 3px rgba(12,122,85,.15); }
.tsp-off  { background:#c3ced8; }
.tsp-empty { text-align:center; padding:44px 20px; color:var(--muted); background:var(--surface); border:1px dashed var(--line); border-radius:var(--radius); }
.tsp-empty-title { font-size:.94rem; font-weight:700; color:var(--text); margin-top:10px; }
.tsp-empty-desc  { font-size:.78rem; margin-top:4px; }

/* ── Plotly card wrapper ─────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--surface) !important;
  border:1px solid var(--line) !important;
  border-radius:var(--radius) !important;
  box-shadow:var(--shadow);
  padding:14px 18px;
}

/* ── Native widget restyle ───────────────────────────────────────── */
[data-baseweb="input"],[data-baseweb="base-input"],
[data-testid="stTextInputRootElement"],[data-testid="stNumberInputContainer"],
[data-testid="stTextAreaRootElement"] {
  background:var(--surface) !important;
  border-radius:var(--radius-sm) !important;
  border-color:var(--line) !important;
}
[data-baseweb="input"]:focus-within {
  border-color:var(--navy) !important;
  box-shadow:0 0 0 3px rgba(0,74,124,.12) !important;
}
input,textarea { color:var(--text) !important; font-size:.82rem !important; }
[data-baseweb="select"] > div { background:var(--surface) !important; border-radius:var(--radius-sm) !important; border-color:var(--line) !important; font-size:.82rem; }
[data-testid="stNumberInputStepUp"],[data-testid="stNumberInputStepDown"] { background:var(--blue-soft) !important; color:var(--navy) !important; }
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
  border-radius:var(--radius-sm); border:1px solid var(--line);
  background:var(--surface); color:var(--navy);
  font-size:.79rem; font-weight:700; padding:.45rem 1rem;
  font-family:'Plus Jakarta Sans',sans-serif;
  transition:background .15s, border-color .15s, transform .12s;
}
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover { border-color:var(--navy); background:var(--blue-soft); }
[data-testid="stButton"] button[kind="primary"] { background:var(--navy); border-color:var(--navy); color:#fff; box-shadow:0 2px 8px rgba(0,74,124,.25); }
[data-testid="stButton"] button[kind="primary"]:hover { background:var(--navy-dark); transform:translateY(-1px); }
[data-testid="stBaseButton-pills"] {
  border-radius:999px !important; font-size:.73rem !important;
  border:1px solid var(--line) !important;
  background:var(--surface) !important; color:var(--text) !important;
}
[data-testid="stBaseButton-pills"][aria-checked="true"] {
  background:var(--navy) !important; color:#fff !important; border-color:var(--navy) !important;
}
[data-testid="stProgress"] > div > div { background:var(--navy); }
div[data-testid="stExpander"] details { border-radius:var(--radius); border:1px solid var(--line); background:var(--surface); box-shadow:var(--shadow); overflow:hidden; }
div[data-testid="stExpander"] details summary { font-size:.82rem; font-weight:700; color:var(--ink); }
div[data-testid="stExpander"] details summary:hover { color:var(--navy); }
[data-testid="stDataFrame"] { border-radius:var(--radius-sm); overflow:hidden; border:1px solid var(--line); }
[data-testid="stAlertContainer"] { border-radius:var(--radius-sm); font-size:.8rem; }
[data-testid="stChatMessage"] { border-radius:var(--radius-sm); padding:8px 12px; background:var(--surface); border:1px solid var(--line); box-shadow:var(--shadow); }
[data-testid="stChatInput"] textarea { font-size:.82rem; }
[data-testid="stSpinner"] { color:var(--navy); }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:4px; background:var(--tint); border-radius:var(--radius-sm); padding:4px; }
[data-testid="stTabs"] [data-baseweb="tab"] { border-radius:9px; font-size:.8rem; font-weight:600; color:var(--muted); padding:6px 14px; }
[data-testid="stTabs"] [aria-selected="true"] { background:var(--surface) !important; color:var(--navy) !important; box-shadow:var(--shadow); }
</style>
""", unsafe_allow_html=True)

# ── Pages ────────────────────────────────────────────────────────────────
from pages.p_scrape    import page_scrape     # noqa: E402
from pages.p_dashboard import page_dashboard  # noqa: E402
from pages.p_ai        import page_ai         # noqa: E402

page = st.navigation([
    st.Page(page_scrape,    title="Scrape & Analisis", icon=":material/radar:"),
    st.Page(page_dashboard, title="Dashboard",         icon=":material/insights:"),
    st.Page(page_ai,        title="AI Insight",        icon=":material/auto_awesome:"),
], position="sidebar")

# ── Sidebar custom shell ─────────────────────────────────────────────────
import base64 as _b64

_logo = _pl.Path("assets/taspen.svg")
if _logo.exists():
    _b = _b64.b64encode(_logo.read_bytes()).decode()
    brand = (
        f'<img src="data:image/svg+xml;base64,{_b}" alt="Taspen" '
        f'style="height:28px;object-fit:contain;">'
    )
else:
    brand = '<div style="font-weight:900;color:var(--navy);">TSP</div>'

_sb_status = ui.engine_status()
_df = st.session_state.get("df")
_vol = len(_df) if _df is not None else 0
_sb_foot = ui.sidebar_footer(volume=_vol, total=max(_vol, 100000))
st.sidebar.markdown(
    ui.sidebar_shell(brand, _sb_status, "", _sb_foot),
    unsafe_allow_html=True,
)
st.logo("assets/taspen.svg")
page.run()
