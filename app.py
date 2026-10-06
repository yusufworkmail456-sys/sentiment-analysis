#!/usr/bin/env python3
"""Streamlit UI: Sentiment Analysis - multi-platform sentiment analysis dashboard.

Left:  Tabs [Scrape & Analisis (incl. credential mgmt), Dashboard]
Right: AI Insight (exec summary + reco + chatbot) - sticky

Jalankan: ./venv/bin/streamlit run app.py --server.port 9120 --server.address 127.0.0.1
"""
import re
import sys
import time
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import httpx

sys.path.insert(0, str(Path(__file__).parent))
from multiscrape import dedupe, scrape_ig, scrape_web, scrape_yt  # noqa: E402
from scrapers_extra import (  # noqa: E402
    scrape_facebook, scrape_tiktok, scrape_playstore,
    save_session, check_session, test_facebook, test_tiktok,
)
from categorize import classify_df  # noqa: E402
import config  # noqa: E402
from icons import icon, icon_text, dot, badge
import icons as ic

# Load IG credentials from UI form into env (for scraper fallback)
try:
    from scrapers_extra import _load_session as _ig_load_session
    _ig_creds = _ig_load_session("instagram")
    if isinstance(_ig_creds, dict):
        if _ig_creds.get("username") and not os.environ.get("IG_USER"):
            os.environ["IG_USER"] = _ig_creds["username"]
        if _ig_creds.get("password") and not os.environ.get("IG_PASS"):
            os.environ["IG_PASS"] = _ig_creds["password"]
except Exception:
    pass

MODEL_NAME = config.MODEL_NAME
OUT_DIR = Path(__file__).parent / "hasil"
OUT_DIR.mkdir(exist_ok=True)

LLM_BASE_URL = config.LLM_BASE_URL
LLM_MODEL = config.LLM_MODEL


LLM_API_KEY = config.LLM_API_KEY


def _load_ig_session():
    """Load IG session dict directly — check_session() only returns 'ok'/'not_setup'."""
    try:
        from scrapers_extra import _load_session
        s = _load_session("instagram")
        return s if isinstance(s, dict) else {}
    except Exception:
        return {}


LABELS = ("Positif", "Netral", "Negatif")
LABEL_COLOR = {"Positif": "#2ecc71", "Netral": "#95a5a6", "Negatif": "#e74c3c"}
LABEL_DOT = {"Positif": ic.C_POSITIF, "Netral": ic.C_NETRAL, "Negatif": ic.C_NEGATIF}
LABEL_ID = {"positive": "Positif", "neutral": "Netral", "negative": "Negatif"}
SOURCE_LABEL = {
    "instagram": "Instagram", "youtube": "YouTube", "web": "Web berita",
    "facebook": "Facebook", "tiktok": "TikTok", "playstore": "Play Store",
}
SOURCE_ICON = {
    "instagram": "instagram", "youtube": "youtube", "web": "web",
    "facebook": "facebook", "tiktok": "tiktok", "playstore": "playstore",
}
DOMAIN_STOPWORDS = {
    "taspen", "pensun", "pensiun", "pns", "asn", "pegawai", "negeri",
    "sipil", "badan", "usaha", "milik", "negara", "bumn",
}
FONT_PATH = str(Path(__file__).parent / "assets" / "fonts" / "DejaVuSans.ttf")

st.set_page_config(page_title="Sentiment Analysis", layout="wide")

# === Compact theme ===
st.markdown("""
<style>
  :root {
    --ss-primary: #3498db;
    --ss-primary-dark: #2980b9;
    --ss-ink: #0b1120;
    --ss-text: #1e293b;
    --ss-muted: #64748b;
    --ss-success: #22c55e;
    --ss-warning: #f59e0b;
    --ss-danger: #ef4444;
    --ss-positif: #2ecc71;
    --ss-netral: #95a5a6;
    --ss-negatif: #e74c3c;
  }
  [data-testid="stHeader"] {display: none;}
  #MainMenu, footer {visibility: hidden;}
  .block-container {padding-top: 0.5rem; padding-bottom: 1rem; max-width: 100%;}
  [data-testid="stMetric"] {
      background: rgba(52,152,219,0.04);
      border: 1px solid rgba(52,152,219,0.12);
      border-radius: 6px;
      padding: 4px 8px !important;
  }
  [data-testid="stMetricLabel"] p {font-size: 0.72rem; opacity: 0.8; margin-bottom: 0;}
  [data-testid="stMetricValue"] {font-size: 1.1rem;}
  [data-testid="stMetricDelta"] {font-size: 0.7rem;}
  div[data-testid="stExpander"] details {border-radius: 6px;}
  [data-testid="stChatMessage"] {border-radius: 8px; padding: 4px 8px;}
  .stTabs [data-baseweb="tab-list"] {gap: 4px;}
  .stTabs [data-baseweb="tab"] {padding: 4px 10px; font-size: 0.85rem; border-radius: 6px 6px 0 0;}
  h1 {font-size: 1.4rem; margin-bottom: 0.2rem;}
  h2 {font-size: 1.15rem; margin-bottom: 0.15rem;}
  h3 {font-size: 1rem; margin-bottom: 0.1rem;}
  h4 {font-size: 0.88rem; margin-bottom: 0.1rem;}
  p, li {font-size: 0.82rem; line-height: 1.35;}
  .stCaption {font-size: 0.72rem;}
  [data-testid="stTextInput"], [data-testid="stNumberInput"] {margin-bottom: 0.2rem;}
  .stSlider > div {padding-top: 0; padding-bottom: 0;}
  [data-testid="stButton"] button {padding: 4px 12px; font-size: 0.82rem;}
  /* Sticky right column */
  div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stChatMessage"]),
  .sticky-right {position: sticky; top: 0;}
  .ss-card-title {font-size: 0.88rem; font-weight: 700; color: var(--ss-text); margin-bottom: 0.1rem;}
  .ss-card-desc {font-size: 0.72rem; color: var(--ss-muted); margin-bottom: 0.3rem;}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------- model
@st.cache_resource(show_spinner="Memuat model sentiment...")
def load_model():
    from transformers import pipeline
    return pipeline("text-classification", model=MODEL_NAME,
                    truncation=True, max_length=128, device=-1)


def run_sentiment(df, progress=None):
    clf = load_model()
    texts = df["text"].astype(str).tolist()
    labels, scores = [], []
    B = 16
    for i in range(0, len(texts), B):
        batch = texts[i:i + B]
        res = clf(batch)
        labels += [r["label"] for r in res]
        scores += [round(r["score"], 4) for r in res]
        if progress is not None:
            progress.progress(min(1.0, (i + B) / max(len(texts), 1)),
                              text=f"Sentiment {min(i+B, len(texts))}/{len(texts)}")
    df["label"] = [LABEL_ID.get(str(l).lower(), l) for l in labels]
    df["score"] = scores
    df["keyakinan"] = ["yakin" if s >= 0.6 else "ragu" for s in scores]
    df = classify_df(df)
    return df


# ------------------------------------------------------- insight & terms
STOP = set("""yang dan di ke dari ini itu ada akan pada juga saya kami kita kamu
dia mereka nya punya untuk dengan tidak sebagai karena agar kalau jika saja masih
lebih sangat oleh atau apa sih dong deh kok ya nih tuh gitu gtu aja udah dah kalo
biar sama gue gw lu loe emang memang cuma doang banget gak ga nggak ngga enggak gk
tak bukan belum jangan tanpa the and of to in is it for on with yang sudah harus
bisa bisa saat ketika semua banyak kalu udh aq ak u mu kah lah pun je kalau
kenapa gimana gmana mana apa apakah itu itu tadi baru nanti langsung terus
jadi seperti kayak gini begitu kali dikit sedikit banget bgt kali ya ok oke
http https www com id co""".split())
NEGATORS = {"tidak", "gak", "nggak", "enggak", "ga", "gk", "kurang", "jangan",
            "belum", "tanpa", "bukan"}


def top_terms(texts, topn=8, exclude=()):
    uni, bi = Counter(), Counter()
    for t in texts:
        toks = [w for w in re.findall(r"[a-zA-Zà-ÿ']{3,}", t.lower())
                if w not in STOP and w not in exclude]
        uni.update(w for w in toks if w not in NEGATORS)
        for a, b in zip(toks, toks[1:]):
            if a in NEGATORS or b in NEGATORS:
                bi.update([f"{a} {b}"])
    terms = [(w, c) for w, c in uni.most_common(topn)]
    for w, c in bi.most_common(4):
        if c >= 2 and not any(w in t for t, _ in terms):
            terms.append((w, c))
    return terms[:topn]


def build_insights(df, exclude=()):
    total = len(df)
    cnt = df["label"].value_counts()
    pct = {k: 100 * cnt.get(k, 0) / total for k in LABELS}
    skor = pct["Positif"] - pct["Negatif"]
    dom = cnt.idxmax()
    out = [f"**{dom}** — {cnt.get(dom,0)}/{total} ({pct[dom]:.0f}%). "
           f"Skor **{skor:+.0f}** (−100 s/d +100)."]
    ragu = int((pd.to_numeric(df["score"], errors="coerce") < 0.6).sum())
    if ragu:
        out.append(f"{icon('warning', 14, ic.C_WARNING)} {ragu} data ({100*ragu/total:.0f}%) skor <0.6 (mungkin meleset).")
    g = df.groupby("source").agg(n=("text","size"), neg=("label", lambda s:(s=="Negatif").sum()))
    g = g[g["n"] >= 5]
    if len(g):
        g["share"] = 100 * g["neg"] / g["n"]
        top = g.sort_values("share", ascending=False).iloc[0]
        if top["share"] >= 20:
            out.append(f"{dot(ic.C_NEGATIF, 8)} Keluhan di **{SOURCE_LABEL.get(top.name,top.name)}**: {top['share']:.0f}% negatif.")
    neg_texts = df.loc[df["label"]=="Negatif","text"].astype(str).tolist()
    if len(neg_texts) >= 3:
        terms = top_terms(neg_texts, 5, exclude=exclude)
        if terms:
            out.append("Negatif: " + ", ".join(f"`{w}`({c}×)" for w,c in terms[:4]))
    if "kategori" in df.columns:
        cat_neg = df[df["label"]=="Negatif"]["kategori"].value_counts()
        if len(cat_neg) and cat_neg.iloc[0] > 0:
            out.append(f"{icon('clipboard', 14, ic.C_PRIMARY)} Kategori keluhan terbanyak: **{cat_neg.index[0]}** ({cat_neg.iloc[0]}).")
    return out


def build_sentiment_context(df, meta):
    if df is None or df.empty:
        return "Belum ada data sentiment. Jalankan analisis dulu."
    total = len(df)
    cnt = df["label"].value_counts()
    pct = {k: round(100*cnt.get(k,0)/total,1) for k in LABELS}
    skor = round(pct["Positif"]-pct["Negatif"],1)
    parts = [
        f"=== KONTEKS SENTIMENT ===",
        f"Keyword: {meta.get('keyword','?')}", f"Total: {total}",
        f"Distribusi: P {pct['Positif']}% ({cnt.get('Positif',0)}), "
        f"N {pct['Netral']}% ({cnt.get('Netral',0)}), "
        f"Neg {pct['Negatif']}% ({cnt.get('Negatif',0)})",
        f"Skor: {skor:+.1f} (−100 s/d +100)",
        f"Sumber: {', '.join(f'{SOURCE_LABEL.get(s,s)}={n}' for s,n in df.groupby('source').size().items())}",
    ]
    if "kategori" in df.columns:
        cat_cnt = df.groupby(["kategori","label"]).size().unstack(fill_value=0)
        parts.append("\nKategori × Sentimen:")
        for cat in cat_cnt.index:
            row = cat_cnt.loc[cat]
            parts.append(f"  {cat}: P={row.get('Positif',0)}, N={row.get('Netral',0)}, Neg={row.get('Negatif',0)}")
    parts.append("\nInsight:")
    kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}", str(meta.get("keyword","")).lower()))
    for b in build_insights(df, exclude=kw_terms):
        parts.append(f"  - {b}")
    parts.append("\nContoh komentar per label (3 teratas by likes):")
    for lab in LABELS:
        sub = df[df["label"]==lab].sort_values("likes",ascending=False).head(3)
        for _, r in sub.iterrows():
            parts.append(f"  [{lab}] (likes={r['likes']},skor={r['score']},sumber={r['source']},kat={r.get('kategori','?')}): {str(r['text'])[:200]}")
    neg_t = df.loc[df["label"]=="Negatif","text"].astype(str).tolist()
    pos_t = df.loc[df["label"]=="Positif","text"].astype(str).tolist()
    if len(neg_t) >= 3:
        parts.append(f"\nTopik negatif: {', '.join(f'{w}({c})' for w,c in top_terms(neg_t,6,exclude=kw_terms))}")
    if len(pos_t) >= 3:
        parts.append(f"Topik positif: {', '.join(f'{w}({c})' for w,c in top_terms(pos_t,6,exclude=kw_terms))}")
    parts.append("\n=== END ===")
    return "\n".join(parts)


# === LLM ===
def chat_completion_sync(messages, temperature=0.4, max_tokens=2000):
    """Returns (content, reasoning) tuple. reasoning is "" if model doesn't support it."""
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
            json={"model": LLM_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        resp.raise_for_status()
        text = resp.text.strip()
        if "data: [DONE]" in text:
            text = text.split("data: [DONE]")[0].strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(text)
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")
        return content, reasoning


def generate_executive_summary(df, meta):
    context = build_sentiment_context(df, meta)
    messages = [
        {"role": "system", "content": (
            "Kamu adalah Senior Sentiment Analyst. "
            "Buat EXECUTIVE SUMMARY untuk manajemen senior. "
            "Format: 2-3 paragraf, bahasa Indonesia formal-profesional. "
            "Struktur: (1) Ringkasan temuan + skor, (2) Kategori/area perlu perhatian, "
            "(3) Catatan kualitas data. Jangan mengarang data. Hanya dari context."
        )},
        {"role": "user", "content": f"{context}\n\nBuat executive summary."},
    ]
    content, _ = chat_completion_sync(messages, temperature=0.3, max_tokens=800)
    return content


def generate_recommendations(df, meta):
    context = build_sentiment_context(df, meta)
    messages = [
        {"role": "system", "content": (
            "Kamu adalah Strategic Advisor. "
            "Buat CONSIDERATION & RECOMMENDATION dari hasil sentiment. "
            "Format Bahasa Indonesia:\n## Consideration\n- 3-5 poin strategis\n"
            "## Recommendation\n- 3-5 rekomendasi actionable (specific, time-bound)\n"
            "Hanya dari data. Jangan mengarang."
        )},
        {"role": "user", "content": f"{context}\n\nBuat consideration & recommendation."},
    ]
    content, _ = chat_completion_sync(messages, temperature=0.4, max_tokens=1200)
    return content




# ================================================================ PDF EXPORT
def export_pdf(df, meta, ai_summary=None, ai_reco=None):
    """Export dashboard charts + AI insight to PDF using kaleido + fpdf2."""
    import tempfile, os
    from fpdf import FPDF

    # Prepare data
    total = len(df)
    cnt = df["label"].value_counts()
    pct = {k: round(100 * cnt.get(k, 0) / total, 1) for k in LABELS}
    skor = round(pct["Positif"] - pct["Negatif"], 1)
    gss = round((cnt.get("Positif", 0) + 0.5 * cnt.get("Netral", 0)) / total * 100, 1)
    kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}", str(meta.get("keyword", "")).lower()))

    charts = []

    # 1. Sentiment Pie
    pie_df = cnt.reindex(list(LABELS)).dropna().rename_axis("label").reset_index(name="n")
    fig = px.pie(pie_df, names="label", values="n", hole=0.55, color="label", color_discrete_map=LABEL_COLOR)
    fig.update_traces(textinfo="label+percent", sort=False)
    fig.update_layout(margin=dict(t=5, b=5, l=5, r=5), height=300, showlegend=False)
    charts.append(("Komposisi Sentimen", fig))

    # 2. Per Source
    src_data = df.groupby(["source", "label"]).size().unstack(fill_value=0)
    for lab in LABELS:
        if lab not in src_data.columns: src_data[lab] = 0
    src_data = src_data.reindex(columns=list(LABELS))
    src_data.index = [SOURCE_LABEL.get(s, s) for s in src_data.index]
    fig = go.Figure()
    for lab in LABELS:
        fig.add_trace(go.Bar(name=lab, x=list(src_data.index), y=src_data[lab].tolist(), marker_color=LABEL_COLOR[lab]))
    fig.update_layout(barmode="group", height=300, margin=dict(t=5, b=5, l=5, r=5), showlegend=True)
    charts.append(("Sentimen per Sumber", fig))

    # 3. ABSA
    if "kategori" in df.columns:
        absa_data = df.groupby(["kategori", "label"]).size().unstack(fill_value=0)
        for lab in LABELS:
            if lab not in absa_data.columns: absa_data[lab] = 0
        absa_data = absa_data.reindex(columns=list(LABELS))
        absa_pct = absa_data.div(absa_data.sum(axis=1), axis=0) * 100
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Positif %", y=list(absa_pct.index), x=absa_pct["Positif"].tolist(),
            orientation="h", marker_color="#2ecc71"))
        fig.add_trace(go.Bar(name="Negatif %", y=list(absa_pct.index), x=(-absa_pct["Negatif"]).tolist(),
            orientation="h", marker_color="#e74c3c"))
        fig.update_layout(barmode="overlay", height=350, margin=dict(t=5, b=5, l=5, r=5),
            xaxis_title="% Sentiment", xaxis=dict(tickformat=",.0f", range=[-100, 100]))
        charts.append(("ABSA: Diverging per Kategori", fig))

    # 4. Heatmap
    if "kategori" in df.columns:
        heat_data = df.groupby(["kategori", "label"]).size().unstack(fill_value=0)
        for lab in LABELS:
            if lab not in heat_data.columns: heat_data[lab] = 0
        heat_data = heat_data.reindex(columns=list(LABELS))
        fig = px.imshow(heat_data.values, x=list(heat_data.columns), y=list(heat_data.index),
            color_continuous_scale="RdYlGn_r", text_auto=True, aspect="auto")
        fig.update_layout(height=350, margin=dict(t=5, b=5, l=5, r=5))
        charts.append(("Heatmap: Kategori x Sentimen", fig))

    # 5. Timeline
    df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    dated = df.dropna(subset=["date_parsed"])
    if len(dated) >= 5:
        dated = dated.copy()
        dated["date_day"] = dated["date_parsed"].dt.date
        tl_data = dated.groupby(["date_day", "label"]).size().unstack(fill_value=0)
        for lab in LABELS:
            if lab not in tl_data.columns: tl_data[lab] = 0
        tl_data = tl_data.reindex(columns=list(LABELS)).sort_index()
        fig = go.Figure()
        for lab in LABELS:
            fig.add_trace(go.Scatter(x=tl_data.index, y=tl_data[lab], mode="lines+markers", name=lab,
                line=dict(color=LABEL_COLOR[lab], width=2)))
        fig.update_layout(height=300, margin=dict(t=5, b=5, l=5, r=5))
        charts.append(("Timeline", fig))

    # 6. Channel Scorecard (as image of table)
    score_data = []
    for src, g in df.groupby("source"):
        n = len(g)
        p = (g["label"] == "Positif").sum()
        ng = (g["label"] == "Negatif").sum()
        nt = (g["label"] == "Netral").sum()
        gss_src = round((p + 0.5 * nt) / n * 100, 1)
        score_data.append({"Channel": SOURCE_LABEL.get(src, src), "Volume": n,
            "Pos%": round(100*p/n,1), "Neg%": round(100*ng/n,1), "GSS": gss_src})
    score_df = pd.DataFrame(score_data).sort_values("GSS", ascending=False)
    fig = go.Figure(go.Table(
        header=dict(values=list(score_df.columns), fill_color="#3498db", font=dict(color="white", size=12)),
        cells=dict(values=[score_df[c] for c in score_df.columns], fill_color="white", height=25)))
    fig.update_layout(height=200, margin=dict(t=5, b=5, l=5, r=5))
    charts.append(("Channel Scorecard", fig))

    # Build PDF
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font("DejaVu", "", config.FONT_REGULAR)
    pdf.add_font("DejaVu", "B", config.FONT_BOLD)

    # Cover page
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 15, "Sentiment Analysis Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 11)
    pdf.ln(5)
    pdf.cell(0, 7, f"Keyword: {meta.get('keyword', '?')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Total data: {total}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"GSS: {gss:.1f}/100  |  Skor: {skor:+.1f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Positif: {pct['Positif']}%  |  Netral: {pct['Netral']}%  |  Negatif: {pct['Negatif']}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Alert badges
    if "kategori" in df.columns:
        cat_neg_pct = df[df["label"]=="Negatif"].groupby("kategori").size() / df.groupby("kategori").size() * 100
        critical = cat_neg_pct[cat_neg_pct >= 50].sort_values(ascending=False)
        if len(critical) > 0:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 7, "ALERT - Kategori Kritis (>50% negatif):", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("DejaVu", "", 10)
            for cat, pv in critical.items():
                pdf.cell(0, 6, f"  [!] {cat}: {pv:.0f}% negatif", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # Chart pages
    for title, fig in charts:
        pdf.add_page()
        pdf.set_font("DejaVu", "B", 13)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        try:
            img_bytes = fig.to_image(format="png", width=900, height=500, scale=2)
            tmp_path = "/tmp/chart_export.png"
            with open(tmp_path, "wb") as f:
                f.write(img_bytes)
            pdf.image(tmp_path, x=15, w=180)
        except Exception as e:
            pdf.set_font("DejaVu", "", 10)
            pdf.cell(0, 7, f"[chart error: {e}]", new_x="LMARGIN", new_y="NEXT")

    # AI Insight page
    if ai_summary or ai_reco:
        pdf.add_page()
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "AI Insight", new_x="LMARGIN", new_y="NEXT")
        if ai_summary:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 7, "Executive Summary", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("DejaVu", "", 10)
            # Strip markdown
            clean = re.sub(r'[*#`]', '', str(ai_summary))
            pdf.multi_cell(0, 5, clean)
            pdf.ln(3)
        if ai_reco:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 7, "Consideration & Recommendation", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("DejaVu", "", 10)
            clean = re.sub(r'[*#`]', '', str(ai_reco))
            pdf.multi_cell(0, 5, clean)

    # Output
    out_path = "/tmp/sentiment_report.pdf"
    pdf.output(out_path)
    with open(out_path, "rb") as f:
        return f.read()
# ================================================================ MAIN
st.markdown('<div style="display:flex;align-items:center;gap:10px;"><img src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjwhLS0gQ3JlYXRlZCB3aXRoIElua3NjYXBlIChodHRwOi8vd3d3Lmlua3NjYXBlLm9yZy8pIC0tPgoKPHN2ZwogICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgIHhtbG5zOmNjPSJodHRwOi8vY3JlYXRpdmVjb21tb25zLm9yZy9ucyMiCiAgIHhtbG5zOnJkZj0iaHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1yZGYtc3ludGF4LW5zIyIKICAgeG1sbnM6c3ZnPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIgogICB4bWxuczpzb2RpcG9kaT0iaHR0cDovL3NvZGlwb2RpLnNvdXJjZWZvcmdlLm5ldC9EVEQvc29kaXBvZGktMC5kdGQiCiAgIHhtbG5zOmlua3NjYXBlPSJodHRwOi8vd3d3Lmlua3NjYXBlLm9yZy9uYW1lc3BhY2VzL2lua3NjYXBlIgogICB3aWR0aD0iOTc2LjcyMjg0IgogICBoZWlnaHQ9IjQzNi42MDc0MiIKICAgdmlld0JveD0iMCAwIDI1OC40MjQ1OCAxMTUuNTE5MDUiCiAgIHZlcnNpb249IjEuMSIKICAgaWQ9InN2ZzgiCiAgIGlua3NjYXBlOnZlcnNpb249IjAuOTIuNCAoNWRhNjg5YzMxMywgMjAxOS0wMS0xNCkiCiAgIHNvZGlwb2RpOmRvY25hbWU9IlRhc3BlbiAoMjAxOSkuc3ZnIj4KICA8ZGVmcwogICAgIGlkPSJkZWZzMiIgLz4KICA8c29kaXBvZGk6bmFtZWR2aWV3CiAgICAgaWQ9ImJhc2UiCiAgICAgcGFnZWNvbG9yPSIjZmZmZmZmIgogICAgIGJvcmRlcmNvbG9yPSIjNjY2NjY2IgogICAgIGJvcmRlcm9wYWNpdHk9IjEuMCIKICAgICBpbmtzY2FwZTpwYWdlb3BhY2l0eT0iMC4wIgogICAgIGlua3NjYXBlOnBhZ2VzaGFkb3c9IjIiCiAgICAgaW5rc2NhcGU6em9vbT0iMC4yNDc0ODczNyIKICAgICBpbmtzY2FwZTpjeD0iNjk3LjU2NTU4IgogICAgIGlua3NjYXBlOmN5PSI0MTQuMzEyMzciCiAgICAgaW5rc2NhcGU6ZG9jdW1lbnQtdW5pdHM9Im1tIgogICAgIGlua3NjYXBlOmN1cnJlbnQtbGF5ZXI9ImxheWVyMSIKICAgICBzaG93Z3JpZD0iZmFsc2UiCiAgICAgZml0LW1hcmdpbi10b3A9IjAiCiAgICAgZml0LW1hcmdpbi1sZWZ0PSIwIgogICAgIGZpdC1tYXJnaW4tcmlnaHQ9IjAiCiAgICAgZml0LW1hcmdpbi1ib3R0b209IjAiCiAgICAgdW5pdHM9InB4IgogICAgIGlua3NjYXBlOndpbmRvdy13aWR0aD0iMTM2NiIKICAgICBpbmtzY2FwZTp3aW5kb3ctaGVpZ2h0PSI3NDUiCiAgICAgaW5rc2NhcGU6d2luZG93LXg9Ii04IgogICAgIGlua3NjYXBlOndpbmRvdy15PSItOCIKICAgICBpbmtzY2FwZTp3aW5kb3ctbWF4aW1pemVkPSIxIiAvPgogIDxtZXRhZGF0YQogICAgIGlkPSJtZXRhZGF0YTUiPgogICAgPHJkZjpSREY+CiAgICAgIDxjYzpXb3JrCiAgICAgICAgIHJkZjphYm91dD0iIj4KICAgICAgICA8ZGM6Zm9ybWF0PmltYWdlL3N2Zyt4bWw8L2RjOmZvcm1hdD4KICAgICAgICA8ZGM6dHlwZQogICAgICAgICAgIHJkZjpyZXNvdXJjZT0iaHR0cDovL3B1cmwub3JnL2RjL2RjbWl0eXBlL1N0aWxsSW1hZ2UiIC8+CiAgICAgICAgPGRjOnRpdGxlPjwvZGM6dGl0bGU+CiAgICAgIDwvY2M6V29yaz4KICAgIDwvcmRmOlJERj4KICA8L21ldGFkYXRhPgogIDxnCiAgICAgaW5rc2NhcGU6bGFiZWw9IkxheWVyIDEiCiAgICAgaW5rc2NhcGU6Z3JvdXBtb2RlPSJsYXllciIKICAgICBpZD0ibGF5ZXIxIgogICAgIHRyYW5zZm9ybT0idHJhbnNsYXRlKDEwNi44NTAzNCwtMTk0LjI2MzY1KSI+CiAgICA8cGF0aAogICAgICAgaWQ9InBhdGg4MzQiCiAgICAgICBzdHlsZT0iZmlsbDojMDA1ZDk3O2ZpbGwtb3BhY2l0eToxO3N0cm9rZS13aWR0aDowLjA1ODgwMTY0IgogICAgICAgZD0ibSAxMTAuNTE5NzQsMjkyLjIyNjUxIGMgLTAuMDIxNiwtMC4wMjE0IC0wLjAzOTIsLTkuOTU4NCAtMC4wMzkyLC0yMi4wODE4OCAwLC0yMC45MzgxNCAwLjAwNCwtMjIuMDQ0NzIgMC4xMDI4NiwtMjIuMDgzNzcgMC4wNTY3LC0wLjAyMjYgMi44MjgzNiwtMC43NzA2NCA2LjE1OTQ4LC0xLjY2MjI2IGwgNi4wNTY1NiwtMS42MjExMSAwLjAyOTQsMi45ODgzMiAwLjAyOTQsMi45ODgzMSAwLjU1ODYsLTAuNTYzOTIgYyAyLjQyODM1LC0yLjQ1MTQgNi4wNzgxLC00LjA3Nzg5IDEwLjI5MDMsLTQuNTg1NzggMS4wNjg0MSwtMC4xMjg4MyAzLjUxMzYsLTAuMTc3ODMgNC41NTcxNCwtMC4wOTEzIDQuMDY3MjUsMC4zMzcxNyA3LjEyMDI3LDEuNjMyNTIgOS4zODA5MSwzLjk4MDE2IDIuMjEzOTEsMi4yOTkwOCAzLjMwMzg3LDUuMDM3NjQgMy43MzA2NSw5LjM3MzMgMC4xNzUxNCwxLjc3OTE4IDAuMjExNzksNS40NTc0OSAwLjE5NDU3LDE5LjUyMTk1IGwgLTAuMDE3LDEzLjg0Nzc5IC02LjM2NTI5LDAuMDE1IC02LjM2NTI4LDAuMDE0OSAtNS44ZS00LC0xNC41OTc3OCBjIC01LjllLTQsLTguOTE4MDEgLTAuMDIzNCwtMTUuMDQzOSAtMC4wNTkyLC0xNS43NDQ0IC0wLjEwMTcxLC0xLjk4Mjk4IC0wLjI2OTI4LC0yLjk4NzE2IC0wLjY2MTc5LC0zLjk2NDY5IC0xLjAxMTc0LC0yLjUxOTc4IC0zLjE4Mzc5LC0zLjk1OTE5IC02LjUyMzI4LC00LjMyMjk0IC0wLjgwNTk5LC0wLjA4NzggLTIuNTIwNjcsLTAuMDc2IC0zLjQ1NjkyLDAuMDIzNiAtMS41MDQ0MiwwLjE2MDE3IC0zLjEwNjQzLDAuNTM4NDIgLTQuMjkyNSwxLjAxMzUgbCAtMC41NTg2NCwwLjIyMzc2IC0wLjAxNDcsMTguNjg0MjMgLTAuMDE0NywxOC42ODQyMyBoIC02LjM0MDY5IGMgLTMuNDg3MzgsMCAtNi4zNTgzMywtMC4wMTc2IC02LjM3OTg5LC0wLjAzOTIgeiBtIC0xOTkuMjAwNDIyLDAuNTMyODQgYyAtMC4xNDU1MjcsLTAuMDEyMiAtMC42MDg1OTUsLTAuMDUgLTEuMDI5MDIyLC0wLjA4NCAtMi4yODYyMDcsLTAuMTg1MTkgLTQuMzUxNywtMC42OTE1NSAtNS44NjMxNzQsLTEuNDM3NDEgLTEuOTc2ODk2LC0wLjk3NTU1IC0zLjMyMzMxOSwtMi4zNDk2MSAtNC4zMDkyNDQsLTQuMzk3NzEgLTAuNzY0MjI4LC0xLjU4NzU0IC0xLjAxNjQ5OCwtMi42Mzc3NyAtMS4yNzQ1NzgsLTUuMzA1ODYgLTAuMDQ4OCwtMC41MDQ0MSAtMC4wNzQ2LC00LjU3NDU5IC0wLjA5MDMsLTE0LjI3NDExIGwgLTAuMDIyMSwtMTMuNTY4NDcgaCAtMi43OTA2MyAtMi43OTA2MSB2IC0zLjA0MzA1IC0zLjA0MzA1IGwgMC44MDg1MSwtMC4yMjY3NyBjIDEuNDI2MDIsLTAuMzk5OTMgMi40ODY3LC0wLjg3NjQyIDMuNjEyNjcsLTEuNjIyOTEgMi44OTk4MTEsLTEuOTIyNTQgNC44NzY4OTksLTQuOTUxNTQgNS42NjI3ODYsLTguNjc1NjkgMC4wODE5NCwtMC4zODgxIDAuMTgzMzk3LC0wLjgzNzkzIDAuMjI1NTQ4LC0wLjk5OTYzIGwgMC4wNzY2MSwtMC4yOTQgMy45NTA1NzcsLTAuMDE1MSAzLjk1MDU3NSwtMC4wMTUyIHYgNS40Mzk1NiA1LjQzOTU2IGggNi40OTc1NzUgYyAzLjU3MzY3MywwIDYuNDk3NTg1LDAuMDE1NyA2LjQ5NzU4NSwwLjAzNDggMCwwLjAxOTIgLTAuOTA1ODY3LDEuNjA2NjUgLTIuMDEzMDM4LDMuNTI3NzIgbCAtMi4wMTMwNDQsMy40OTI4OCAtNC40Njk4MzgsMC4wMTUxIC00LjQ2OTg0LDAuMDE1MiAtMC4wMTY0NCwxMS45NjYxNCBjIC0wLjAxNjU0LDEyLjAzODI5IDAuMDA2MywxMy44MzU4OCAwLjE5MTI1MiwxNC45MDYyMSAwLjIyODc2NiwxLjMyNTQ1IDAuNjg2NDQsMi4yODk5MSAxLjQzNzAzNSwzLjAyODI4IDEuMDE4MjQ5LDEuMDAxNjcgMi4xOTA5NDEsMS4zOTc3NSA0LjMwMTIxNiwxLjQ1MjcyIDEuODI4NTQ4LDAuMDQ3NyAzLjIwNTkyNCwtMC4xNjU5NCA0LjgxODI1MSwtMC43NDcxMSAwLjkyMDY0LC0wLjMzMTg0IDAuODY2MTk3LC0wLjMxOTk3IDAuOTAyNTc1LC0wLjE5NjQ3IDAuMDE3NDksMC4wNTk1IDAuNDg1Njg0LDEuNjEyNjkgMS4wNDAzMzEsMy40NTE0MSAwLjU1NDY0MSwxLjgzODcxIDAuOTg2MDYzLDMuMzY0MDEgMC45NTg3MDUsMy4zODk1NiAtMC4wOTcyNiwwLjA5MDkgLTEuNzUwNzA4LDAuNTk3NDMgLTIuNjg2MjAyLDAuODIzMDQgLTEuNjcwNTA3LDAuNDAyODYgLTMuMjYzODM5LDAuNjY3NzggLTUuMTU0NzQ4LDAuODU3MDUgLTAuOTEwNzIxLDAuMDkxMiAtNS4yMDIxMywwLjE2ODcgLTUuOTM4OTY4LDAuMTA3MjkgeiBtIDQwLjA0MzkzMywtNy4xNjc0OSBjIDAuODgxNTExLC0wLjEyMjIzIDEuNTk5Mzc2LC0wLjI3OTU0IDIuMzA3OTY4LC0wLjUwNTczIGwgMC41NzMzMTYsLTAuMTgzMDIgdiAtNi44MzY2MiAtNi44MzY2MiBsIC0wLjMwODcwOSwtMC4wNDE0IGMgLTAuNTkzOTIyLC0wLjA3OTcgLTMuNTg0MjQzLC0wLjEzNjc4IC00LjYyNzAyNiwtMC4wODgzIC0xLjE2ODQ4OSwwLjA1NDIgLTEuNzYyNzUxLDAuMTIzMjkgLTIuNTg3NTQ5LDAuMzAwNTkgLTIuNzI0MDY3LDAuNTg1NTkgLTQuNjA3NDA3LDIuMjU5ODggLTUuMjg4NDI3LDQuNzAxNDEgLTAuNDI2Mzc5LDEuNTI4NjMgLTAuNDMwODcyLDMuNjU4OTUgLTAuMDEwODMsNS4xMjQyNSAwLjczNzk4NCwyLjU3NDMzIDIuNzA2MTIxLDQuMDQ4MjcgNS45NDI3Myw0LjQ1MDUxIDAuNjQ3MTM1LDAuMDgwNSAzLjE5NjIzLDAuMDI2MiAzLjk5ODUxLC0wLjA4NSB6IG0gLTkuODE5ODc0LDcuMjU3MTQgYyAtNC43NjA1MjUsLTAuMjc2NTUgLTguNTQwMjIzLC0yLjIzMTc5IC0xMC43ODk1MDUsLTUuNTgxNDMgLTAuNDA0MDIzLC0wLjYwMTY3IC0xLjA2OTA5MiwtMS45NDY3MyAtMS4zMjI4OTksLTIuNjc1NDggLTAuODM1MjM2LC0yLjM5ODE2IC0xLjA0Mzg4LC01LjMyMjI0IC0wLjU4NTI5NywtOC4yMDI4MyAwLjQ3NTA4NiwtMi45ODQyOSAxLjgwMDU2NywtNS40NjkyMiAzLjg2MTg1MywtNy4yMzk5NyAzLjMwNjk1NSwtMi44NDA4NyA3LjQzMDE4NCwtMy44NzQ1MiAxNS40NTAyMDEsLTMuODczMjUgMS44MDMxNTcsMCA0LjkxNjE3MSwwLjA4MTkgNS42OTU0NjMsMC4xNDk0OCBsIDAuNDAyNDg5LDAuMDM0OCAtMC4wMjc1LC0zLjE2NDcgYyAtMC4wMjg5NywtMy4zMjg5NSAtMC4wNjI0NCwtMy44MTM3MSAtMC4zMzkwNzIsLTQuOTA2MDIgLTAuNTUwNjk3LC0yLjE3NDU1IC0yLjA0Njc1LC0zLjUyNDI4IC00LjU1NDQ5OCwtNC4xMDkwNSAtMS43MzMxMjUsLTAuNDA0MTYgLTQuNjA2NzU1LC0wLjQ2MjMxIC03LjA4NTU5OSwtMC4xNDMzOSAtMi4xNDA4MiwwLjI3NTQgLTQuMzkxNzQxLDAuODgxMjYgLTYuMDIwOTg2LDEuNjIwNTkgLTAuMzU5MTUyLDAuMTYyOTggLTAuNjk0MTY4LDAuMzA5MDcgLTAuNzQ0NDcxLDAuMzI0NjYgLTAuMDczMDgsMC4wMjI2IC0wLjM0ODg3OSwtMC42NjM0NyAtMS4zNzIxMDQsLTMuNDEzMzcgLTAuNzA0MzQxLC0xLjg5MjkzIC0xLjI5Mzk3MiwtMy40OTI3MSAtMS4zMTAyOCwtMy41NTUwOSAtMC4wMjUsLTAuMDk1NCAwLjA0MzI3LC0wLjE0MTI3IDAuNDMxMjY5LC0wLjI4OTYzIDIuODg3NjU5LC0xLjEwNDE4IDYuODk2NDksLTEuODgwODMgMTEuNjAzODQyLC0yLjI0ODA3IDEuMzA5NDI1LC0wLjEwMjEzIDUuMTMyMDExLC0wLjE0MDk1IDYuMzUwNTgxLC0wLjA2NDQgNC43Mjk1NywwLjI5NjkgOC4xODE0NDcsMS4zNDMyNyAxMC43MjAzMTcsMy4yNDk2MyAwLjY2MzY4NiwwLjQ5ODM1IDEuNzUzOTc5LDEuNjE1MTIgMi4yMzA5MTMsMi4yODUwOCAwLjc4MDk1OSwxLjA5NzA0IDEuNDQ3OTIyLDIuNjI5NDIgMS43Mzk5NzYsMy45OTc2NyAwLjU2MTQ3LDIuNjMwNDcgMC42MDczNjMsNC40NDg3NCAwLjU4NDc1NywyMy4xNjc4NSBsIC0wLjAxNjk1LDE0LjAyNDIgLTUuOTI0MjcxLDAuMDE1IC01LjkyNDI2MywwLjAxNTEgdiAtMS45NDk2MyAtMS45NDk2MSBsIC0wLjU3MzMxNSwwLjU1MzQ5IGMgLTIuMzk1NTYsMi4zMTI3NiAtNS45NDUzNDMsMy42OTA1MiAtMTAuMTI4NTkyLDMuOTMxMTEgLTEuMTI1NDYzLDAuMDY0NiAtMS4xOTMzOTMsMC4wNjQ1IC0yLjM1MjA2MSwtMC4wMDMgeiBNIDkwLjk0MDE2NSwyNjEuOTA5NCBjIC0wLjAyMTI1LC0xLjIxMzA4IC0wLjA2OTA0LC0yLjIzMjE4IC0wLjEyNjA0NywtMi42ODQ5OCAtMC41NTcxMzQsLTQuNDI3NzggLTIuMjAxMzM5LC02LjY0NjMxIC01LjQxMjQzOCwtNy4zMDMwMyAtMS43MTg1NjUsLTAuMzUxNDYgLTMuOTY2NjUyLC0wLjIwNTQgLTUuNDEwMzE4LDAuMzUxNTYgLTIuNTE1MTEyLDAuOTcwMjkgLTQuMDgwODA3LDMuNTg1NTIgLTQuNTgxMDYsNy42NTE4OSAtMC4xMzkyMjEsMS4xMzE3MiAtMC4yNzE2ODUsMy41MDk1MiAtMC4yMTcwMTMsMy44OTU1OSAwLjAwMzQsMC4wMjQzIDMuNTU1NTkxLDAuMDQ0MSA3Ljg5MzY2NywwLjA0NDEgaCA3Ljg4NzQyIHogbSAtNy4zMDI1ODksMzAuOTk2OTkgYyAtOS42MDEwOCwtMC41MTczMiAtMTYuMDExNjUxLC00LjI4MDYyIC0xOS4xMTMyMDQsLTExLjIyMDMzIC0xLjE3MjQ2OCwtMi42MjM0IC0xLjg0ODk2OCwtNS41MzU4OCAtMi4xNTIyMzgsLTkuMjY1ODggLTAuMDk0NSwtMS4xNjIzMiAtMC4wOTUzMywtNC41OTA4NyAtMC4wMDE1LC01LjY3NDM1IDAuMzY0MDMzLC00LjE5Nzg4IDEuMjE1MTEsLTcuNTA4NDUgMi43MTM0NTQsLTEwLjU1NDkyIDEuMDM1NzM0LC0yLjEwNTg1IDIuMTQ2ODE2LC0zLjY2Mzk4IDMuNzMxODU2LC01LjIzMzM1IDMuMDY5MjU5LC0zLjAzODg2IDcuMDcyNzcsLTQuNzk1MTEgMTIuMjA0ODM3LC01LjM1Mzk0IDEuMTc4NzYsLTAuMTI4MzYgMy45NTQ5NDUsLTAuMTc1ODEgNS4yMzMzNDYsLTAuMDg5NSA0LjM3MDgsMC4yOTUyNSA3LjY5MzE2MiwxLjQwODAyIDEwLjQzNzI5OSwzLjQ5NTc2IDAuNjQxNjU2LDAuNDg4MTcgMS43NjYyNTIsMS41ODg1NyAyLjM1MTA1OCwyLjMwMDQ3IDIuNDEwNDE2LDIuOTM0MjUgMy42NjUzNjYsNi4yNzg3OSA0LjIwMzE0NiwxMS4yMDE3IDAuMjA0MzUsMS44NzA5MyAwLjI0MzMyLDIuNjAxMTkgMC4yNzgyOSw1LjIxODY2IGwgMC4wMzM5LDIuNTQzMTYgSCA4OS4zNDkzNDYgNzUuMTQwNyBsIDAuMDAxNSwwLjMzODExIGMgMC4wMDI4LDAuOTAwODUgMC4xMjYyODMsMi43NDU1MSAwLjIzMjIwMiwzLjQ2OTEzIDAuMzI5MDQzLDIuMjQ4MDMgMS4wNjE4MDksNC4yMzM1IDIuMTY0Nzk3LDUuODY1NjQgMS45OTA3NjUsMi45NDU4MyA0Ljk5NDg1Miw0LjYzOTI2IDkuMzAzNDczLDUuMjQ0NDYgMS4wNTQwNjIsMC4xNDgwNiA0LjMwNDI0NywwLjE0NzA5IDUuNTU0NTQyLC0wLjAwMiAyLjU0MDk5NCwtMC4zMDIyOSA1LjA3ODUwNCwtMC45NjQ3MSA2LjU0ODE3NywtMS43MDk0NCAwLjE2NzQzOSwtMC4wODQ5IDAuMzA0NDMzLC0wLjE0MzM2IDAuMzA0NDMzLC0wLjEzIDAsMC4wMTM0IDAuNTUyMTIzLDEuNTI4NjYgMS4yMjY5NDYsMy4zNjczOCAwLjY3NDgxLDEuODM4NzEgMS4yNDUxMiwzLjQwMTQ5IDEuMjY3MzYsMy40NzI4NCAwLjAzNDcsMC4xMTEzMiA2ZS00LDAuMTQ5ODQgLTAuMjQyMDEsMC4yNzE2NSAtMS4yNDQ4NywwLjYyNTYzIC0zLjg4MjM4NCwxLjM2NDc3IC02LjQyNzIxNywxLjgwMTE4IC0zLjM2NTA1MywwLjU3NzA3IC03LjkxNDg3NiwwLjgzMjk0IC0xMS40MzY5MjYsMC42NDMxNyB6IG0gLTk2LjkwNTEyNywwLjAyNTYgYyAtNS4wMTEwMDYsLTAuMTk5OTEgLTkuNTYyMzAzLC0xLjAwOTA4IC0xMi42OTU5NzcsLTIuMjU3MjQgLTAuMzQyNDI2LC0wLjEzNjM5IC0wLjYyMjU5OCwtMC4yNjY5NyAtMC42MjI1OTgsLTAuMjkwMTkgMCwtMC4wNTczIDIuNTgzNTI3LC03LjE5MDA1IDIuNjE2MDU4LC03LjIyMjU5IDAuMDE0MTcsLTAuMDE0MiAwLjM1MDg4NiwwLjEyMDI3IDAuNzQ4MjIsMC4yOTg3OSAyLjg0NjQwNywxLjI3ODg4IDYuODM3MjYyLDIuMDQzNDMgMTAuNjU5OTE3LDIuMDQyMTUgNC4wMzkzNjgyLC0wLjAwMiA2LjU5MDE5NzYsLTEuMTIxMDcgNy40NjY0MjM0LC0zLjI3NzQ3IDAuMzA3NDcyNSwtMC43NTY2OCAwLjM5ODE4MjEsLTEuODEyOTQgMC4yMzU3MDksLTIuNzQ0NjQgLTAuMjY0MTU2MiwtMS41MTQ3NCAtMS4wOTUwNzIxLC0yLjQ0MjQ0IC0zLjIzMzIxMTgsLTMuNjA5NzkgLTAuMzU1NzQ3OCwtMC4xOTQyMiAtMi41MTIyOTg2LC0xLjM1MDY5IC00Ljc5MjMzMzYsLTIuNTY5OTQgLTUuMDIwNDIyLC0yLjY4NDY1IC01LjUzNTUzOSwtMi45ODQxMSAtNi44ODM0NjcsLTQuMDAxNDkgLTEuNzg0MDUxLC0xLjM0NjYgLTMuMDQwMjM1LC0yLjc5NjAyIC0zLjg5Njg5NiwtNC40OTYzNCAtMC45ODU1MDYsLTEuOTU2MDcgLTEuMzkzNzE4LC00LjAwMjE1IC0xLjMxMzQ5NSwtNi41ODM2IDAuMDQ3ODUsLTEuNTM5NzIgMC4yMjgzNzUsLTIuNjYwODMgMC42Mjk2MzQsLTMuOTEwMzEgMS40ODU2OTEsLTQuNjI2MTYgNS41NzIxMzIsLTcuNTc2MiAxMS43Mjg4MzMsLTguNDY3MTggMS41NjQ5MTMsLTAuMjI2NDUgMi41ODM2NDUsLTAuMjg5MjIgNC42MTU5Mjc1LC0wLjI4NDMzIDMuODMwMjcyOCwwLjAxIDcuMjgyMDY2NzIsMC40MTM2IDEwLjQzNzI5ODUsMS4yMjI4NSAxLjU4NDk5ODgsMC40MDY1MSAzLjI2MzQ4NTEsMC45NzYxNCAzLjI2MzQ4NTEsMS4xMDc1MiAwLDAuMDM2NCAtMC42MDE5Nzg1LDEuNjYyNDcgLTEuMzM3NzMzLDMuNjEzNTQgLTEuMDM5OTA3NCwyLjc1NzU5IC0xLjM1NzM4MDgsMy41NDE0IC0xLjQyNTk0MjYsMy41MjA1NSAtMC4wNDg1NDcsLTAuMDE0NyAtMC4zODUzNzU0LC0wLjE2MTY2IC0wLjc0ODU5NTksLTAuMzI2NDYgLTEuMjMxMTQwMTcsLTAuNTU4NTcgLTMuMjM4MDE3NCwtMS4xNzQ3NiAtNC43Nzg3NTUxLC0xLjQ2NzI3IC0yLjkyODU5MzQsLTAuNTU1OTggLTYuMDI2MTA1MiwtMC41MTQzIC03LjkyNjMzMzUsMC4xMDY2NyAtMS43NTcwOTksMC41NzQxOSAtMi44NjI2NSwxLjY0NjM2IC0zLjE2NTEyOSwzLjA2OTUyIC0wLjE0NzczNiwwLjY5NTA4IC0wLjA4ODA5LDEuNzY1MjUgMC4xMzQwNzUsMi40MDU1MiAwLjMyODUxNiwwLjk0Njc3IDAuOTU1MDE4LDEuNjc0MzcgMi4wOTMyMzEsMi40MzA5OCAwLjkwNjY0NSwwLjYwMjY4IDEuNzIwMTIyMywxLjAzOTA3IDUuMTMwMjQ2NiwyLjc1MjExIDUuNjg4MzEwMzEsMi44NTc0NSA2LjU1MDU2OTMxLDMuMzMxNTggNy45MjI2NDU4LDQuMzU2NDIgMi44OTQyMDE0LDIuMTYxNzUgNC41MDE3ODU1LDQuNzQ4NTMgNS4wMTQ2MDMyLDguMDY4OTkgMC4yNDAxNDY5LDEuNTU0OTcgMC4xNjYwNDI4LDMuODk2MTUgLTAuMTc2OTM5OCw1LjU5MDEgLTEuMzE0OTc0Miw2LjQ5NDQxIC02Ljg0MjM1Mjg3LDEwLjM2ODk5IC0xNS41NTMzODMsMTAuOTAyNiAtMC44Njk0Njg2LDAuMDUzMiAtMy4wNTM3NTc4LDAuMDY0IC00LjE0NTUxNjgsMC4wMjA2IHogbSA0Ni40NDIxMjIsLTcuMTk0MTMgYyA2LjUxMDQ0OSwtMC45NjYwOSAxMC4wNDU1MjUsLTUuODM1NzIgMTAuNTY0MjU5LC0xNC41NTI0NSAwLjE4OTExNiwtMy4xNzc5MiAtMC4wNzMzLC02LjM2Mzc3IC0wLjczMTQyOCwtOC44OCAtMC4yODMwMzIsLTEuMDgyMDkgLTAuNTY5OTY0LC0xLjg2ODIzIC0xLjA0MDU1NiwtMi44NTA4OCAtMS42NzY0MzgsLTMuNTAwNjUgLTQuMzk2NjcxLC01LjQyOTUyIC04LjIxNzA2MSwtNS44MjY1NiAtMC45Mjk0ODEsLTAuMDk2NiAtMi45MjY3NjgsLTAuMDM3NiAtMy45MzM4NzQsMC4xMTYzOCAtMS4yMjg3NSwwLjE4Nzc2IC0yLjM3NjM1NCwwLjUwOTMyIC0zLjMxODg0MywwLjkyOTk2IGwgLTAuMzM4MTE1LDAuMTUwOSB2IDE1LjI3NTUxIDE1LjI3NTUxIGwgMC41MzE2NTksMC4xMjQ4IGMgMS43NjgwMzEsMC40MTUwOCA0LjU4ODQ0OCwwLjUxODEgNi40ODM5NTksMC4yMzY4MyB6IG0gLTE5LjY1Nzk3MiwtNi44MjMxIGMgMCwtMTYuOTc3MyAwLjAxMDQzLC0zMC44Njc4MSAwLjAyMzEzLC0zMC44Njc4MSAwLjAxMjcxLDAgMi43MzkyNzgsLTAuNzI2NzcgNi4wNTg5NzYsLTEuNjE1MDMgMy4zMTk2OTEsLTAuODg4MjYgNi4wODEwMzQsLTEuNjIyNTUgNi4xMzYzMDksLTEuNjMxNzQgMC4wOTMzMiwtMC4wMTU1IDAuMTAyNjA1LDAuMTg4MjYgMC4xMjk5MDEsMi44NTMzOCBsIDAuMDI5MzcsMi44NzAwOSAwLjM1MjgxLC0wLjQyNTEgYyAwLjUxNjA2OCwtMC42MjE3OCAxLjQyMTMzMSwtMS40MDQ0IDIuMzAyNDMzLC0xLjk5MDQ3IDIuMDAzMDAyLC0xLjMzMjM0IDQuMzA3ODk5LC0yLjE0MDE4IDcuMTY0NjM4LC0yLjUxMTE1IDEuMTYxNTMsLTAuMTUwODEgNC4yMjU2MTUsLTAuMTUxMDEgNS40MDk3NTEsLTMuNGUtNCA0LjI4OTE3MiwwLjU0NTc5IDcuNTM5NzA0LDIuMDc5NzIgMTAuMTUyMjgyLDQuNzkwODggMy4xNDg2NjMsMy4yNjc0OCA0Ljk0Njk4Nyw3Ljk1NjUxIDUuNTI5NTQsMTQuNDE3OTMgMC4xMDQwMjMsMS4xNTM3MyAwLjEwNDA2NSw1LjYzMDYgMCw2LjcwMzM5IC0wLjI0MzgyMSwyLjUxNTIgLTAuNzQwNTk1LDQuOTUwNDIgLTEuNDIxNDUsNi45NjggLTAuNzA2OTA0LDIuMDk0NzkgLTEuODI3Mjc4LDQuMzE4NCAtMy4wMTY5NDcsNS45ODc3MiAtNC4yMTQxOTYsNS45MTMzNyAtMTAuODk4NjUxLDguOTQyNDEgLTE4LjY1MjQ5Nyw4LjQ1MjMzIC0yLjk4ODYxOCwtMC4xODg4OCAtNS4zNzE3OTQsLTAuNzE4MzUgLTYuOTk3NDAyLC0xLjU1NDYyIC0wLjI1ODcyNCwtMC4xMzMxIC0wLjQ5MDI2LC0wLjI1MTA3IC0wLjUxNDUxMywtMC4yNjIxNCAtMC4wMjQyMywtMC4wMTEgLTAuMDQ0MDksMy40MTk5MiAtMC4wNDQwOSw3LjYyNDQyIHYgNy42NDQ1NyBsIC0wLjE5MTEwOCwwLjA2MDcgYyAtMC4xMDUxMDYsMC4wMzMzIC0yLjg3Njg2NiwwLjc3NzYgLTYuMTU5NDcyLDEuNjUzODUgLTMuMjgyNjA0LDAuODc2MjUgLTYuMDQxMTM0LDEuNjE3IC02LjEzMDA3MywxLjY0NjA4IGwgLTAuMTYxNzAxLDAuMDUzIHYgLTMwLjg2NzgxIHoiCiAgICAgICBpbmtzY2FwZTpjb25uZWN0b3ItY3VydmF0dXJlPSIwIiAvPgogICAgPHBhdGgKICAgICAgIHN0eWxlPSJmaWxsOiMwMDVkOTc7ZmlsbC1vcGFjaXR5OjE7c3Ryb2tlLXdpZHRoOjAuMDU4ODAxNjQiCiAgICAgICBkPSJtIDU3LjY4MzAyNiwyNDkuODg0NDEgYyAtMC4yNjg1OTUsLTAuNTU3MTIgLTEuMDE5MzAxLC0xLjg0NzcxIC0xLjQ4MjgzLC0yLjU0OTI1IC0zLjI3OTM5LC00Ljk2MzMgLTcuODg4MjYxLC04LjMyOTg0IC0xMy43NTI1MDgsLTEwLjA0NTQzIC0yLjQxNDM4NywtMC43MDYzMyAtNS4zNjMzNywtMS4xODAzOSAtOC4wNjMwNjksLTEuMjk2MTYgLTUuNjYyMTE5LC0wLjI0Mjc5IC0xMC4yODExNTgsLTEuMDE4MzMgLTE0LjM2NTUxNywtMi40MTE5MSAtMy4xNjgwNDUsLTEuMDgwOTMgLTYuMTE0MTQ3LC0yLjY2MzI2IC04LjUzNTQ4LC00LjU4NDMxIC0yLjg4MTYwMzEsLTIuMjg2MjEgLTUuMzQxMzIwNCwtNS4zOTk0NSAtNy4xOTQzOTIzLC05LjEwNTg2IC0yLjMwNDUzNjQsLTQuNjA5MzggLTMuODM4MjM4NzgsLTEwLjQ2NTYxIC00LjYxNTAxNzY2LC0xNy42MjE3MiAtMC4zMzk1MDMxOCwtMy4xMjc2OCAtMC42MTM5NjU3NywtNy43MzU1MiAtMC40Njc5ODAxOSwtNy44NTY1OSAwLjA0MTM5MzEsLTAuMDM0MyA3LjA5NzcxNjM1LC0wLjA0ODIgMTguNjEwNzI1MTUsLTAuMDM2NSBsIDE4LjU0NDA4NiwwLjAxODggMC45MTEzNTQsMC4xMzEzNiBjIDIuMzA0MDA4LDAuMzMyMDggNC4xMzMzMDIsMC44OTkxNyA2LjIwMzY0NiwxLjkyMzE0IDMuMjM5ODY0LDEuNjAyNDUgNi4xMTA5NjEsNC4wNzMwNCA4LjQ3MTY5Niw3LjI4OTkyIDIuNzMxNjY3LDMuNzIyMzUgNC42MDMyNzQsOC4yMzg1MyA1LjQzNDI1MiwxMy4xMTI3OSAwLjE1NTUsMC45MTIxIDAuMjIzODk2LDEuNDQwNjggMC40MjIzMDMsMy4yNjM0OSAwLjA4MDE5LDAuNzM2OTIgMC4xNDA5MjIsMzAuMDQ3NjUgMC4wNjIyMiwzMC4wNDc2NSAtMC4wMjY4OCwwIC0wLjEwOTQ0NywtMC4xMjU2OSAtMC4xODM1MTEsLTAuMjc5MzEgeiIKICAgICAgIGlkPSJwYXRoODMyIgogICAgICAgaW5rc2NhcGU6Y29ubmVjdG9yLWN1cnZhdHVyZT0iMCIgLz4KICAgIDxwYXRoCiAgICAgICBpZD0icGF0aDg1MiIKICAgICAgIGQ9Im0gNjMuNTYzMTk1LDI0OS44ODQ0MSBjIDAuMjY4NTkzLC0wLjU1NzEyIDEuMDE5MzAyLC0xLjg0NzcxIDEuNDgyODMsLTIuNTQ5MjUgMy4yNzkzOSwtNC45NjMzIDcuODg4MjYxLC04LjMyOTg0IDEzLjc1MjUyLC0xMC4wNDU0MyAyLjQxNDQsLTAuNzA2MzMgNS4zNjMzOTEsLTEuMTgwMzkgOC4wNjMwODgsLTEuMjk2MTYgNS42NjIxMiwtMC4yNDI3OSAxMC4yODExNjMsLTEuMDE4MzMgMTQuMzY1NTE3LC0yLjQxMTkxIDMuMTY4MDQsLTEuMDgwOTMgNi4xMTQxNCwtMi42NjMyNiA4LjUzNTQ4LC00LjU4NDMxIDIuODgxNiwtMi4yODYyMSA1LjM0MTMyLC01LjM5OTQ1IDcuMTk0NCwtOS4xMDU4NiAyLjMwNDUyLC00LjYwOTM4IDMuODM4MjMsLTEwLjQ2NTYxIDQuNjE1MDIsLTE3LjYyMTcyIDAuMzM5NDksLTMuMTI3NjggMC42MTM5NiwtNy43MzU1MiAwLjQ2Nzk3LC03Ljg1NjU5IC0wLjA0MTQsLTAuMDM0MyAtNy4wOTc3MiwtMC4wNDgyIC0xOC42MTA3MiwtMC4wMzY1IGwgLTE4LjU0NDA5LDAuMDE4OCAtMC45MTEzNTQsMC4xMzEzNiBjIC0yLjMwNDAxNiwwLjMzMjA4IC00LjEzMzMxNCwwLjg5OTE3IC02LjIwMzY2OSwxLjkyMzE0IC0zLjIzOTg3NCwxLjYwMjQ1IC02LjExMDk2OCw0LjA3MzA0IC04LjQ3MTcwNSw3LjI4OTkyIC0yLjczMTY2NiwzLjcyMjM1IC00LjYwMzI3NCw4LjIzODUzIC01LjQzNDI1MiwxMy4xMTI3OSAtMC4xNTU1LDAuOTEyMSAtMC4yMjM4OTYsMS40NDA2OCAtMC40MjIzMDIsMy4yNjM0OSAtMC4wODAxOSwwLjczNjkyIC0wLjE0MDkyMywzMC4wNDc2NSAtMC4wNjIyMiwzMC4wNDc2NSAwLjAyNjg3LDAgMC4xMDk0NDgsLTAuMTI1NjkgMC4xODM1MTEsLTAuMjc5MzEgeiIKICAgICAgIHN0eWxlPSJmaWxsOiNlOGMyMWQ7ZmlsbC1vcGFjaXR5OjE7c3Ryb2tlLXdpZHRoOjAuMDU4ODAxNjQiCiAgICAgICBpbmtzY2FwZTpjb25uZWN0b3ItY3VydmF0dXJlPSIwIiAvPgogICAgPHBhdGgKICAgICAgIHN0eWxlPSJmaWxsOiNkMWFlMjQ7ZmlsbC1vcGFjaXR5OjE7c3Ryb2tlLXdpZHRoOjAuMDU4ODAxNjQiCiAgICAgICBkPSJtIDYyLjkxMDk2OCwyNTAuMTU4MDMgYyAtNS45ZS00LC0wLjAxOTMgMC4xMjA1MzgsLTAuNDAyOTkgMC4yNjkwNDUsLTAuODUyNjIgMC44NzY3MzksLTIuNjU0MzkgMi4zMTExNDEsLTUuNjU5NjggMy43Njk0NDEsLTcuODk3NTYgMS41NjY5MjcsLTIuNDA0NTkgMy4wMTgxMjIsLTMuOTg1MTIgNS41Njc2MDYsLTYuMDYzODQgMC43NzIzMzIsLTAuNjI5NzIgMS41OTQ1ODgsLTEuMzAzNzEgMS44MjcyNDEsLTEuNDk3NzYgMC4yMzI2NDgsLTAuMTk0MDIgMC41NDAwOTIsLTAuNDQ5MTkgMC42ODMyMTYsLTAuNTY3MDEgMC4zMTYwNzcsLTAuMjYwMiAyLjA0OTg3NywtMS42ODkxNiAyLjM3NzA4NywtMS45NTkxNCAwLjMwNjM2OSwtMC4yNTI3OSAxLjA4NDI4NiwtMC44OTY0MiAxLjIzNDg1LC0xLjAyMTcgMC4wNjQ2NywtMC4wNTM4IDAuNDcxMDc3LC0wLjM4ODkgMC45MDMwODgsLTAuNzQ0NjUgMC40MzIwMTIsLTAuMzU1NzYgMS4wNTU4NTMsLTAuODcxNzQgMS4zODYzMjEsLTEuMTQ2NjQgMC4zMzA0NjEsLTAuMjc0ODkgMC43MTc4OTEsLTAuNTk1OSAwLjg2MDk1NCwtMC43MTMzMyAwLjE0MzA2MSwtMC4xMTc0MyAwLjUzNzk1MiwtMC40NDQwMSAwLjg3NzUzMiwtMC43MjU3MyAwLjMzOTU3OSwtMC4yODE3MSAwLjcyMzI1OSwtMC41OTkyNSAwLjg1MjYxOSwtMC43MDU2MiAwLjEyOTM2NSwtMC4xMDYzNyAwLjUxMzA0NywtMC40MjM5IDAuODUyNjI2LC0wLjcwNTYxIDAuMzM5NTgsLTAuMjgxNzEgMC43MjMyNjEsLTAuNTk5MjUgMC44NTI2MjcsLTAuNzA1NjMgMC4xMjkzNTgsLTAuMTA2MzcgMC41MTMwMzksLTAuNDIzODkgMC44NTI2MTgsLTAuNzA1NjEgMC4zMzk1OCwtMC4yODE3MiAwLjcyMzI2MSwtMC41OTkyNSAwLjg1MjYyNywtMC43MDU2MyAwLjEyOTM2NiwtMC4xMDYzNiAwLjUwMTcxOSwtMC40MTQ4NCAwLjgyNzQ2NCwtMC42ODU1MSAwLjMyNTczOCwtMC4yNzA2NSAwLjcwNzE2MywtMC41ODQ3MiAwLjg0NzU5OCwtMC42OTc5MSAwLjE0MDQzNywtMC4xMTMxOSAwLjI4NDA2OSwtMC4yMzI1MSAwLjMxOTE3NSwtMC4yNjUxNSAwLjA1NDczLC0wLjA1MDggMS4wMDE2ODIsLTAuODM2NjIgMS43NjkwNzIsLTEuNDY3ODkgMC4xMjkzNTksLTAuMTA2NDEgMC41OTI0MjIsLTAuNDkwMTIgMS4wMjkwMjYsLTAuODUyNjUgMC40MzY2MDMsLTAuMzYyNTQgMC44OTk2NjIsLTAuNzQ2MjIgMS4wMjkwMzIsLTAuODUyNjIgMC4xMjkzNjMsLTAuMTA2NDEgMC41OTI0MywtMC40OTAwOSAxLjAyOTAzMiwtMC44NTI2MiAwLjQzNjYwMiwtMC4zNjI1NCAwLjg5OTY2MSwtMC43NDYyMiAxLjAyOTAyMywtMC44NTI2MyAwLjEyOTM2MiwtMC4xMDY0MSAwLjU5MjQzLC0wLjQ5MDA5IDEuMDI5MDMxLC0wLjg1MjYyIDAuNDM2NjAzLC0wLjM2MjU0IDAuODk5NjYsLTAuNzQ2MjEgMS4wMjkwMzIsLTAuODUyNjMgMC4xMjkzNTQsLTAuMTA2NCAwLjU4MTEwOCwtMC40ODEwNCAxLjAwMzg5OSwtMC44MzI1NSAwLjQyMjc3MiwtMC4zNTE0OCAwLjg4MzI0NSwtMC43MzE2OCAxLjAyMzI2OCwtMC44NDQ4OCAwLjE0MDAxMywtMC4xMTMyIDAuNjgyNjczLC0wLjU2MzA0IDEuMjA1OTAyLC0wLjk5OTYzIDAuNTIzMjMsLTAuNDM2NjEgMS4wNjgyNiwtMC44ODk5MiAxLjIxMTE5LC0xLjAwNzM2IDAuMTQyOTMsLTAuMTE3NDUgMC42MDU3OCwtMC41MDExMyAxLjAyODU1LC0wLjg1MjYzIDAuNDIyNzgsLTAuMzUxNDkgMC44ODMyNSwtMC43MzE3IDEuMDIzMjgsLTAuODQ0ODggMC4xNDAwMiwtMC4xMTMyIDAuNjgyNjcsLTAuNTYzMDMgMS4yMDU4OSwtMC45OTk2MyAwLjUyMzI0LC0wLjQzNjYxIDEuMDY4MjgsLTAuODg5OTQgMS4yMTEyLC0xLjAwNzQgMC4xNDI5NCwtMC4xMTc0NSAwLjY5NjQ4LC0wLjU3NjMyIDEuMjMwMTIsLTEuMDE5NjkgMC41MzM2MSwtMC40NDMzNiAxLjA3NjA1LC0wLjg5MzE5IDEuMjA1NDEsLTAuOTk5NjIgMC4xMjkzNywtMC4xMDY0NCAwLjY3MTgxLC0wLjU1NjI2IDEuMjA1NDMsLTAuOTk5NjQgMC41MzM2NCwtMC40NDMzNiAxLjA3NjA4LC0wLjg5MzUgMS4yMDU0NSwtMS4wMDAzMSAwLjQwNjEzLC0wLjMzNTM4IDQuODU3NDYsLTQuMDI4MjQgNi43NjIxOSwtNS42MDk5NiA0LjI4ODMsLTMuNTYxMTUgNC41NjU1MiwtMy43ODQ5MiA0LjYyMDcxLC0zLjcyOTczIDAuMDYxMiwwLjA2MTMgLTAuMDA0LDEuNzUzMjggLTAuMTU0NTcsMy45NTg0NCAtMS4wODc2NiwxNi4wMTc4NSAtNS40OTkxNiwyNi4xMjc3NCAtMTMuODUxMDYsMzEuNzQyNjcgLTIuNDE2NjQsMS42MjQ3IC01LjQyNDYyLDIuOTk4MSAtOC41MjAxODcsMy44OTAxOSAtMy45MDMxNjUsMS4xMjQ4NCAtNy45MTQ3OTYsMS43MTU5OCAtMTMuMTcxNTc0LDEuOTQwOTEgLTEuOTE3NTk4LDAuMDgxOSAtNC4yODU0MTIsMC40MDYxNCAtNi4yNDY4NjEsMC44NTUwNCAtNy41Mjk5OTYsMS43MjMzIC0xMy4zMjUzNDQsNi4xMDA2NiAtMTYuODEyMDIyLDEyLjY5ODQ5IC0wLjE4ODIxOSwwLjM1NjE3IC0wLjM0MjY1NiwwLjYzMTc4IC0wLjM0MzE5OCwwLjYxMjQ4IHoiCiAgICAgICBpZD0icGF0aDgyOCIKICAgICAgIGlua3NjYXBlOmNvbm5lY3Rvci1jdXJ2YXR1cmU9IjAiIC8+CiAgICA8cGF0aAogICAgICAgaWQ9InBhdGg4NTciCiAgICAgICBkPSJtIDU4LjEzNzA2MSwyNTAuNzE4NiBjIDUuODllLTQsLTAuMDE5NSAtMC4xMjAxNjEsLTAuNDA4NCAtMC4yNjgyMDEsLTAuODY0MSAtMC44NzM5ODYsLTIuNjkwMTUgLTIuMzAzODg1LC01LjczNTkyIC0zLjc1NzYwNiwtOC4wMDM5MyAtMS41NjIwMDgsLTIuNDM2OTcgLTMuMDA4NjQ3LC00LjAzODggLTUuNTUwMTI0LC02LjE0NTUxIC0wLjc2OTkxLC0wLjYzODIgLTEuNTg5NTg1LC0xLjMyMTI2IC0xLjgyMTUwNywtMS41MTc5MiAtMC4yMzE5MTYsLTAuMTk2NjYgLTAuNTM4Mzk1LC0wLjQ1NTI1IC0wLjY4MTA3LC0wLjU3NDY3IC0wLjMxNTA4NiwtMC4yNjM2OSAtMi4wNDM0NDcsLTEuNzExOSAtMi4zNjk2MjgsLTEuOTg1NTMgLTAuMzA1NDA2LC0wLjI1NjE5IC0xLjA4MDg4MywtMC45MDg0OSAtMS4yMzA5NzIsLTEuMDM1NDQgLTAuMDY0NDUsLTAuMDU0NiAtMC40Njk2LC0wLjM5NDE1IC0wLjkwMDI1NCwtMC43NTQ3IC0wLjQzMDY1NiwtMC4zNjA1MyAtMS4wNTI1MzgsLTAuODgzNDcgLTEuMzgxOTY5LC0xLjE2MjA3IC0wLjMyOTQyNCwtMC4yNzg2IC0wLjcxNTYzNywtMC42MDM5MyAtMC44NTgyNSwtMC43MjI5MyAtMC4xNDI2MTIsLTAuMTE5MDMgLTAuNTM2MjYzLC0wLjQ1IC0wLjg3NDc3NywtMC43MzU1MSAtMC4zMzg1MTQsLTAuMjg1NTEgLTAuNzIwOTg5LC0wLjYwNzMyIC0wLjg0OTk0MiwtMC43MTUxMiAtMC4xMjg5NiwtMC4xMDc4MSAtMC41MTE0MzYsLTAuNDI5NjEgLTAuODQ5OTUsLTAuNzE1MTQgLTAuMzM4NTE0LC0wLjI4NTUgLTAuNzIwOTg4LC0wLjYwNzMxIC0wLjg0OTk0OSwtMC43MTUxMSAtMC4xMjg5NTQsLTAuMTA3ODEgLTAuNTExNDI4LC0wLjQyOTYyIC0wLjg0OTk0MiwtMC43MTUxMiAtMC4zMzg1MTQsLTAuMjg1NTIgLTAuNzIwOTksLTAuNjA3MzMgLTAuODQ5OTUsLTAuNzE1MTQgLTAuMTI4OTYsLTAuMTA3NzkgLTAuNTAwMTQ1LC0wLjQyMDQzIC0wLjgyNDg2NiwtMC42OTQ3MyAtMC4zMjQ3MTYsLTAuMjc0MzEgLTAuNzA0OTQyLC0wLjU5MjYgLTAuODQ0OTM3LC0wLjcwNzMzIC0wLjEzOTk5NywtMC4xMTQ3MSAtMC4yODMxNzYsLTAuMjM1NjMgLTAuMzE4MTczLC0wLjI2ODcxIC0wLjA1NDU2LC0wLjA1MTYgLTAuOTk4NTM2LC0wLjg0NzkgLTEuNzYzNTE2LC0xLjQ4NzY3IC0wLjEyODk1NCwtMC4xMDc4NCAtMC41OTA1NjQsLTAuNDk2NyAtMS4wMjU3OTUsLTAuODY0MTIgLTAuNDM1MjMxLC0wLjM2NzQyIC0wLjg5Njg0LC0wLjc1NjI4IC0xLjAyNTgwMSwtMC44NjQxIC0wLjEyODk1OSwtMC4xMDc4NSAtMC41OTA1NjksLTAuNDk2NyAtMS4wMjU4MDEsLTAuODY0MTMgLTAuNDM1MjMxLC0wLjM2NzQyIC0wLjg5Njg0LC0wLjc1NjI2IC0xLjAyNTc5MiwtMC44NjQxIC0wLjEyODk1OSwtMC4xMDc4NCAtMC41OTA1NjksLTAuNDk2NjggLTEuMDI1ODAxLC0wLjg2NDEgLTAuNDM1MjMyLC0wLjM2NzQzIC0wLjg5Njg0MSwtMC43NTYyNyAtMS4wMjU4LC0wLjg2NDExIC0wLjEyODk1MywtMC4xMDc4NCAtMC41NzkyODUsLTAuNDg3NTMgLTEuMDAwNzQ2LC0wLjg0Mzc3IC0wLjQyMTQ0NywtMC4zNTYyMSAtMC44ODA0NzUsLTAuNzQxNTUgLTEuMDIwMDU0LC0wLjg1NjI2IC0wLjEzOTU4LC0wLjExNDcyIC0wLjY4MDUzNywtMC41NzA2IC0xLjIwMjEyMywtMS4wMTMwOSAtMC41MjE1ODUsLTAuNDQyNDkgLTEuMDY0OTAyLC0wLjkwMTg5IC0xLjIwNzM4MywtMS4wMjA5NCAtMC4xNDI0ODEsLTAuMTE5MDIgLTAuNjAzODc2LC0wLjUwNzg2IC0xLjAyNTMzLC0wLjg2NDExIC0wLjQyMTQ1MywtMC4zNTYyMiAtMC44ODA0NzQsLTAuNzQxNTQgLTEuMDIwMDYxLC0wLjg1NjI2IC0wLjEzOTU4LC0wLjExNDcxIC0wLjY4MDUzMSwtMC41NzA2MiAtMS4yMDIxMTUsLTEuMDEzMDkgLTAuNTIxNTkzLC0wLjQ0MjQ5IC0xLjA2NDkxLC0wLjkwMTkyIC0xLjIwNzM5MSwtMS4wMjA5NiAtMC4xNDI0ODIsLTAuMTE5MDUgLTAuNjk0Mjg4LC0wLjU4NDEgLTEuMjI2MjM3LC0xLjAzMzQzIC0wLjUzMTk1LC0wLjQ0OTMzIC0xLjA3MjY5MiwtMC45MDUyMiAtMS4yMDE2NDQsLTEuMDEzMDkgLTAuMTI4OTYsLTAuMTA3ODcgLTAuNjY5NzAxLC0wLjU2Mzc2IC0xLjIwMTY1MSwtMS4wMTMwNyAtMC41MzE5NDksLTAuNDQ5MzYgLTEuMDcyNjkxLC0wLjkwNTU3IC0xLjIwMTY1MSwtMS4wMTM4MiAtMC40MDQ4NjYsLTAuMzM5OSAtNC44NDIyMTIzLC00LjA4MjQ3IC02Ljc0MDk1NDQsLTUuNjg1NTEgLTQuMjc0ODQ0NDIsLTMuNjA5MTMgLTQuNTUxMTk0NjcsLTMuODM1OTEgLTQuNjA2MjA2NjUsLTMuNzc5OTggLTAuMDYxMDYxNiwwLjA2MjIgMC4wMDQ4NiwxLjc3NjkgMC4xNTQwNzgwNyw0LjAxMTc4IDEuMDg0MjQ3MjYsMTYuMjMzNTcgNS40ODE4OTYxOCwyNi40Nzk2NSAxMy44MDc1NjU5OCwzMi4xNzAxOSAyLjQwOTA2MywxLjY0NjU4IDUuNDA3NjAxLDMuMDM4NDkgOC40OTM0NDksMy45NDI2IDMuODkwOTA2LDEuMTM5OTcgNy44ODk5NDIsMS43MzkwOCAxMy4xMzAyMTUsMS45NjcwNSAxLjkxMTU3OCwwLjA4MzEgNC4yNzE5NTcsMC40MTE2IDYuMjI3MjQ4LDAuODY2NTUgNy41MDYzNTgsMS43NDY1MiAxMy4yODM1MSw2LjE4MjgzIDE2Ljc1OTI0MywxMi44Njk1MyAwLjE4NzYyOCwwLjM2MDk3IDAuMzQxNTgsMC42NDAyOSAwLjM0MjEyMSwwLjYyMDcyIHoiCiAgICAgICBzdHlsZT0iZmlsbDojMDA0YTdjO2ZpbGwtb3BhY2l0eToxO3N0cm9rZS13aWR0aDowLjA1OTEwMzM0IgogICAgICAgaW5rc2NhcGU6Y29ubmVjdG9yLWN1cnZhdHVyZT0iMCIgLz4KICA8L2c+Cjwvc3ZnPgo=" height="42" style="vertical-align:middle;"><img src="data:image/jpeg;base64,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" height="38" style="vertical-align:middle;border-radius:4px;"><h1 style="margin:0;">Sentiment Analysis</h1></div>', unsafe_allow_html=True)

# AI panel visibility: hidden (default) → narrow → wide
_ai_state = st.session_state.get("ai_state", "hidden")  # hidden | narrow | wide
_ai_btn_label = {"hidden": "AI", "narrow": "AI [>]", "wide": "AI [>>]"}[_ai_state]

# Top bar: title area + AI toggle button
_top1, _top2 = st.columns([10, 1])
with _top2:
    if st.button(_ai_btn_label, key="btn_ai_toggle", use_container_width=True,
                  help="Klik untuk buka AI Insight"):
        st.session_state["ai_state"] = {"hidden": "narrow", "narrow": "wide", "wide": "hidden"}[_ai_state]
        st.rerun()

# Layout based on AI state
if _ai_state == "hidden":
    _main_area = st.container()
    _ai_area = None
elif _ai_state == "narrow":
    _main_area, _ai_area = st.columns([3, 1], gap="small")
else:  # wide
    _main_area, _ai_area = st.columns([1, 2], gap="small")

# ================================================ MAIN AREA: Tabs
with _main_area:
    tab_scrape, tab_dash = st.tabs(["Scrape & Analisis", "Dashboard"])
    with tab_scrape:
        df = st.session_state.get("df")

        # --- Credential management (inline, compact) ---
        with st.expander("Kredensial Sumber Data", expanded=False):
            cred_c1, cred_c2, cred_c3 = st.columns(3)

            def _status_badge(plat):
                s = check_session(plat)
                if plat in ("youtube", "web", "playstore"):
                    return badge("OK", ic.C_SUCCESS)
                if s == "ok":
                    return badge("OK", ic.C_SUCCESS)
                return badge("OFF", ic.C_MUTED)

            with cred_c1:
                st.markdown(f'{icon_text("instagram", "IG", 16, ic.C_PRIMARY, bold=True)} {_status_badge("instagram")}  ·  {icon_text("youtube", "YT", 16, ic.C_PRIMARY, bold=True)} {badge("OK", ic.C_SUCCESS)}', unsafe_allow_html=True)
                ig_sess = _load_ig_session()
                ig_sid_val = ig_sess.get("session_id", "")
                ig_sid = st.text_input("IG session_id (cara terbaik)", key="ig_sid", value=ig_sid_val, label_visibility="collapsed", placeholder="IG session_id dari browser")
                ig_user_val = ig_sess.get("username", "")
                ig_user = st.text_input("IG username", key="ig_user", value=ig_user_val, label_visibility="collapsed", placeholder="IG username")
                ig_pwd = st.text_input("IG password", type="password", key="ig_pwd", label_visibility="collapsed", placeholder="IG password")
                if st.button("Simpan IG", key="save_ig", help="Simpan & login IG"):
                    data = {}
                    if ig_sid.strip():
                        data["session_id"] = ig_sid.strip()
                        os.environ["IG_SESSIONID"] = ig_sid.strip()
                    if ig_user.strip():
                        data["username"] = ig_user.strip()
                        os.environ["IG_USER"] = ig_user.strip()
                    if ig_pwd:
                        data["password"] = ig_pwd
                        os.environ["IG_PASS"] = ig_pwd
                    if data:
                        # Hapus session file lama
                        from pathlib import Path as _P
                        _sf = _P(__file__).parent / "ig_session.json"
                        if _sf.exists():
                            _sf.unlink()
                        save_session("instagram", data)
                        st.rerun()
                    else:
                        st.error("Isi session_id atau username+password.")

            with cred_c2:
                st.markdown(f'{icon_text("facebook", "FB", 16, ic.C_PRIMARY, bold=True)} {_status_badge("facebook")}  ·  {icon_text("tiktok", "TikTok", 16, ic.C_PRIMARY, bold=True)} {_status_badge("tiktok")}', unsafe_allow_html=True)
                fb_cookie = st.text_area("FB cookie", key="fb_cookie", height=40, label_visibility="collapsed", placeholder="Paste FB cookie (c_user, xs, ...)")
                if st.button("Simpan FB", key="save_fb"):
                    if fb_cookie.strip():
                        ok, msg = test_facebook(fb_cookie.strip())
                        if ok:
                            save_session("facebook", {"cookie": fb_cookie.strip()})
                            st.rerun()
                        else: st.error(msg)

                tt_token = st.text_input("TikTok ms_token", key="tt_token", type="password", label_visibility="collapsed", placeholder="TikTok ms_token")
                if st.button("Simpan TikTok", key="save_tt"):
                    if tt_token.strip():
                        ok, msg = test_tiktok(tt_token.strip())
                        if ok:
                            save_session("tiktok", {"ms_token": tt_token.strip()})
                            st.rerun()
                        else: st.error(msg)

            with cred_c3:
                st.markdown(f'{icon_text("playstore", "Play Store", 16, ic.C_PRIMARY, bold=True)} {badge("OK", ic.C_SUCCESS)}  ·  {icon_text("web", "Web", 16, ic.C_PRIMARY, bold=True)} {badge("OK", ic.C_SUCCESS)}', unsafe_allow_html=True)
                st.caption("Play Store & Web: tanpa login. Review app yang dikonfigurasi otomatis.")

        # --- Config & Run ---
        with st.expander("Konfigurasi", expanded=df is None):
            p = st.pills("Contoh:", ["gojek", "grab", "shopee", "tokopedia"], key="kw_pills")
            if p and p != st.session_state.get("kw_applied"):
                st.session_state["kw_input"] = p
                st.session_state["kw_applied"] = p

            keyword = st.text_input("Keyword", value="taspen", key="kw_input",
                                    help="Contoh: nama brand, produk, atau topik")

            s1, s2, s3, s4, s5, s6 = st.columns(6)
            with s1:
                ig_on = st.toggle("IG", value=True, key="ig_on")
                n_ig = st.number_input("max", 0, 300, 60, 10, key="n_ig", disabled=not ig_on, label_visibility="collapsed")
            with s2:
                yt_on = st.toggle("YT", value=True, key="yt_on")
                n_yt = st.number_input("max", 0, 300, 60, 10, key="n_yt", disabled=not yt_on, label_visibility="collapsed")
            with s3:
                web_on = st.toggle("Web", value=True, key="web_on")
                n_web = st.number_input("max", 0, 30, 8, 1, key="n_web", disabled=not web_on, label_visibility="collapsed")
            with s4:
                ps_on = st.toggle("Play Store", value=True, key="ps_on")
                n_ps = st.number_input("max", 0, 300, 60, 10, key="n_ps", disabled=not ps_on, label_visibility="collapsed")
            with s5:
                fb_on = st.toggle("FB", value=False, key="fb_on")
                n_fb = st.number_input("max", 0, 300, 60, 10, key="n_fb", disabled=not fb_on, label_visibility="collapsed")
            with s6:
                tt_on = st.toggle("TikTok", value=False, key="tt_on")
                n_tt = st.number_input("max", 0, 300, 60, 10, key="n_tt", disabled=not tt_on, label_visibility="collapsed")

            run_scrape = st.button("Mulai Scrape + Analisis", type="primary", use_container_width=True)

        if run_scrape:
            if not keyword.strip():
                st.error("Keyword kosong.")
                st.stop()

            logs, rows = [], []
            t0 = time.time()

            with st.status("Scraping...", expanded=True) as status:
                def log(msg):
                    logs.append(msg)
                    st.write(msg)

                def ambil(nama, fn, n):
                    if n <= 0: return
                    log(f"> {nama}: mulai (target {n})...")
                    try:
                        got = fn(keyword.strip(), n, log)
                        rows.extend(got)
                        log(f"OK {nama}: {len(got)} baris")
                    except Exception as e:
                        log(f"FAIL {nama}: {type(e).__name__} {str(e)[:120]}")

                if ig_on: ambil("Instagram", scrape_ig, n_ig)
                if yt_on: ambil("YouTube", scrape_yt, n_yt)
                if web_on: ambil("Web", scrape_web, n_web)
                if ps_on: ambil("Play Store", scrape_playstore, n_ps)
                if fb_on: ambil("Facebook", scrape_facebook, n_fb)
                if tt_on: ambil("TikTok", scrape_tiktok, n_tt)

                rows = dedupe(rows)
                if not rows:
                    status.update(label="Selesai — tidak ada data", state="error")
                    st.error("Tidak ada data. Coba keyword lain.")
                    st.stop()
                status.update(label=f"Scraping selesai: {len(rows)} baris", state="complete", expanded=False)

            df = pd.DataFrame(rows)
            progress = st.progress(0.0, text="Menyiapkan model...")
            try:
                df = run_sentiment(df, progress)
            finally:
                progress.empty()

            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            out_csv = OUT_DIR / f"sentiment_{keyword.strip().replace(' ', '_')}_{stamp}.csv"
            df.to_csv(out_csv, index=False, encoding="utf-8")
            st.session_state["df"] = df
            st.session_state["out_csv"] = str(out_csv)
            st.session_state["logs"] = logs
            st.session_state["meta"] = {"keyword": keyword.strip(), "stamp": stamp, "durasi": round(time.time() - t0)}
            st.session_state["ai_summary"] = None
            st.session_state["ai_reco"] = None
            st.rerun()

        # --- Results ---
        df = st.session_state.get("df")
        if df is None:
            st.info("Atur parameter, lalu klik **Mulai Scrape + Analisis**.")
        else:
            meta = st.session_state.get("meta", {})
            out_csv = st.session_state.get("out_csv", "")
            kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}", str(meta.get("keyword", "")).lower()))
            df["likes"] = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0).astype(int)
            if "keyakinan" not in df.columns:
                df["keyakinan"] = ["yakin" if s >= 0.6 else "ragu" for s in pd.to_numeric(df["score"], errors="coerce").fillna(0)]
            if "kategori" not in df.columns:
                df = classify_df(df)

            total = len(df)
            cnt = df["label"].value_counts()
            pct = {k: round(100 * cnt.get(k, 0) / total, 1) for k in LABELS}
            skor = round(pct["Positif"] - pct["Negatif"], 1)

            st.markdown(f'**Hasil — {meta.get("keyword", "?")}** · {total} data · {dot(ic.C_POSITIF, 8)} {pct["Positif"]}% {dot(ic.C_NETRAL, 8)} {pct["Netral"]}% {dot(ic.C_NEGATIF, 8)} {pct["Negatif"]}% · skor {skor:+.1f}', unsafe_allow_html=True)

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total", total)
            k2.metric("Positif", f"{pct['Positif']}%")
            k3.metric("Netral", f"{pct['Netral']}%")
            k4.metric("Negatif", f"{pct['Negatif']}%")

            with st.container(border=True):
                for b in build_insights(df, exclude=kw_terms):
                    st.markdown(f"- {b}", unsafe_allow_html=True)

            pie_df = cnt.reindex(list(LABELS)).dropna().rename_axis("label").reset_index(name="n")
            fig = px.pie(pie_df, names="label", values="n", hole=0.55, color="label", color_discrete_map=LABEL_COLOR)
            fig.update_traces(textinfo="label+percent", sort=False)
            fig.update_layout(margin=dict(t=5, b=5, l=5, r=5), height=220, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Contoh komentar per label"):
                for lab in LABELS:
                    sub = df[df["label"] == lab].sort_values("likes", ascending=False).head(2)
                    if sub.empty: continue
                    with st.expander(f"{lab} ({cnt.get(lab,0)})", expanded=(lab == "Negatif")):
                        for _, r in sub.iterrows():
                            warn = " · skor rendah" if r["keyakinan"] == "ragu" else ""
                            st.markdown(f"> {str(r['text'])[:200]}  \n> {SOURCE_LABEL.get(r['source'],r['source'])} · likes:{r['likes']} · skor {r['score']} · {r.get('kategori','?')}{warn}")

            with st.expander("Data + Filter"):
                # Filters
                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    sel_src = st.multiselect("Sumber", options=sorted(df["source"].unique()),
                        default=sorted(df["source"].unique()),
                        format_func=lambda s: SOURCE_LABEL.get(s, s), key="flt_src")
                with f2:
                    sel_lab = st.multiselect("Sentimen", options=list(LABELS),
                        default=list(LABELS), key="flt_lab")
                with f3:
                    if "kategori" in df.columns:
                        sel_cat = st.multiselect("Kategori", options=sorted(df["kategori"].unique()),
                            default=sorted(df["kategori"].unique()), key="flt_cat")
                    else:
                        sel_cat = []
                with f4:
                    search_q = st.text_input("Cari teks", key="flt_search", placeholder="keyword...")

                view = df.copy()
                if sel_src:
                    view = view[view["source"].isin(sel_src)]
                if sel_lab:
                    view = view[view["label"].isin(sel_lab)]
                if sel_cat and "kategori" in df.columns:
                    view = view[view["kategori"].isin(sel_cat)]
                if search_q:
                    view = view[view["text"].astype(str).str.contains(search_q, case=False, na=False)]
                view = view.sort_values(["likes"], ascending=False)

                st.caption(f"{len(view)} dari {len(df)} data")
                st.dataframe(view[["label","score","source","kategori","text","author","likes","url"]],
                    hide_index=True, use_container_width=True, height=250,
                    column_config={
                        "label": st.column_config.TextColumn("Sentimen"),
                        "score": st.column_config.NumberColumn("Skor", format="%.2f"),
                        "source": st.column_config.TextColumn("Sumber"),
                        "kategori": st.column_config.TextColumn("Kategori"),
                        "text": st.column_config.TextColumn("Teks", width="large"),
                        "author": st.column_config.TextColumn("Author"),
                        "likes": st.column_config.NumberColumn("Likes"),
                        "url": st.column_config.LinkColumn("buka", display_text="buka"),
                    })
                csv_bytes = df.to_csv(index=False, encoding="utf-8").encode("utf-8")
                fname = Path(out_csv).name if out_csv else "hasil.csv"
                st.download_button("CSV", csv_bytes, file_name=fname, mime="text/csv")

            with st.expander("Log"):
                st.code("\n".join(st.session_state.get("logs", ["(kosong)"])), language=None)
    # ========== TAB: DASHBOARD ==========
    with tab_dash:
        df = st.session_state.get("df")
        if df is None or df.empty:
            st.info("Jalankan scraping di tab 'Scrape & Analisis' dulu.")
        else:
            # --- PDF Export button ---
            tr1, tr2 = st.columns([4, 1])
            with tr2:
                st.write("")
                export_pdf_btn = st.button("Export PDF", key="btn_pdf", use_container_width=True)

            total = len(df)
            cnt = df["label"].value_counts()
            pct = {k: round(100 * cnt.get(k, 0) / total, 1) for k in LABELS}
            skor = round(pct["Positif"] - pct["Negatif"], 1)
            gss = round((cnt.get("Positif", 0) + 0.5 * cnt.get("Netral", 0)) / total * 100, 1)
            df["likes"] = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0).astype(int)
            if "kategori" not in df.columns:
                df = classify_df(df)
            kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}", str(st.session_state.get("meta", {}).get("keyword", "")).lower()))

            # === PDF Export ===
            if export_pdf_btn:
                with st.spinner("Generating PDF..."):
                    try:
                        pdf_bytes = export_pdf(df, st.session_state.get("meta", {}),
                            st.session_state.get("ai_summary"), st.session_state.get("ai_reco"))
                        st.download_button("Download PDF", pdf_bytes,
                            file_name=f"sentiment_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf", key="dl_pdf")
                        st.success("PDF siap diunduh!")
                    except Exception as e:
                        st.error(f"PDF error: {e}")

            # === ALERT BADGES ===
            if "kategori" in df.columns:
                cat_neg_pct = df[df["label"]=="Negatif"].groupby("kategori").size() / df.groupby("kategori").size() * 100
                critical = cat_neg_pct[cat_neg_pct >= 50].sort_values(ascending=False)
                if len(critical) > 0:
                    alert_html = ""
                    for cat, pct_val in critical.items():
                        alert_html += f"<span style='background:#e74c3c;color:white;padding:2px 8px;border-radius:4px;font-size:0.75rem;margin:2px;'>{cat}: {pct_val:.0f}% negatif</span>"
                    st.markdown(f"<div style='margin-bottom:8px;'>{alert_html}</div>", unsafe_allow_html=True)

            # === METRIC CARDS ===
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", total)
            m2.metric("Positif", f"{pct['Positif']}%")
            m3.metric("Netral", f"{pct['Netral']}%")
            m4.metric("Negatif", f"{pct['Negatif']}%")

            # === ROW 1: GSS Gauge + ABSA Diverging ===
            r1c1, r1c2 = st.columns([1, 2])
            with r1c1:
                with st.container(border=True):
                    st.markdown(f'<div class="ss-card-title">{icon("gauge", 18, ic.C_PRIMARY)} GSS Score</div><div class="ss-card-desc">Skor sentimen keseluruhan (0-100)</div>', unsafe_allow_html=True)
                    st.markdown(f"**{gss:.1f}/100** · Skor {skor:+.1f}")
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number", value=gss,
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "#3498db"},
                            "steps": [
                                {"range": [0, 40], "color": "#e74c3c"},
                                {"range": [40, 60], "color": "#f39c12"},
                                {"range": [60, 80], "color": "#f1c40f"},
                                {"range": [80, 100], "color": "#2ecc71"},
                            ],
                            "threshold": {"line": {"color": "black", "width": 3}, "thickness": 0.75, "value": gss}
                        }
                    ))
                    fig_gauge.update_layout(height=220, margin=dict(t=10, b=5, l=10, r=10))
                    st.plotly_chart(fig_gauge, use_container_width=True)

            with r1c2:
                with st.container(border=True):
                    st.markdown(f'<div class="ss-card-title">{icon("chart", 18, ic.C_PRIMARY)} Sentiment per Kategori</div><div class="ss-card-desc">Persentase positif vs negatif per kategori domain</div>', unsafe_allow_html=True)
                    if "kategori" in df.columns:
                        absa_data = df.groupby(["kategori", "label"]).size().unstack(fill_value=0)
                        for lab in LABELS:
                            if lab not in absa_data.columns: absa_data[lab] = 0
                        absa_data = absa_data.reindex(columns=list(LABELS))
                        absa_pct = absa_data.div(absa_data.sum(axis=1), axis=0) * 100
                        fig_absa = go.Figure()
                        fig_absa.add_trace(go.Bar(name="Positif %", y=list(absa_pct.index), x=absa_pct["Positif"].tolist(),
                            orientation="h", marker_color="#2ecc71"))
                        fig_absa.add_trace(go.Bar(name="Negatif %", y=list(absa_pct.index), x=(-absa_pct["Negatif"]).tolist(),
                            orientation="h", marker_color="#e74c3c"))
                        fig_absa.update_layout(barmode="overlay", height=240, margin=dict(t=5, b=5, l=5, r=5),
                            xaxis_title="% Sentiment", showlegend=True,
                            xaxis=dict(tickformat=",.0f", range=[-100, 100]),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        st.plotly_chart(fig_absa, use_container_width=True)

            # === ROW 2: Per Sumber + Channel Scorecard ===
            r2c1, r2c2 = st.columns(2)
            with r2c1:
                with st.container(border=True):
                    st.markdown(f'<div class="ss-card-title">{icon("dashboard", 18, ic.C_PRIMARY)} Persebaran per Sumber</div><div class="ss-card-desc">Komposisi sentimen tiap platform</div>', unsafe_allow_html=True)
                    src_data = df.groupby(["source", "label"]).size().unstack(fill_value=0)
                    for lab in LABELS:
                        if lab not in src_data.columns: src_data[lab] = 0
                    src_data = src_data.reindex(columns=list(LABELS))
                    src_data.index = [SOURCE_LABEL.get(s, s) for s in src_data.index]
                    fig_bar = go.Figure()
                    for lab in LABELS:
                        fig_bar.add_trace(go.Bar(name=lab, x=list(src_data.index), y=src_data[lab].tolist(), marker_color=LABEL_COLOR[lab]))
                    fig_bar.update_layout(barmode="stack", height=240, margin=dict(t=5, b=5, l=5, r=5), showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    st.plotly_chart(fig_bar, use_container_width=True)

            with r2c2:
                with st.container(border=True):
                    st.markdown(f'<div class="ss-card-title">{icon("trophy", 18, ic.C_PRIMARY)} Channel Scorecard</div><div class="ss-card-desc">Ranking platform berdasarkan GSS</div>', unsafe_allow_html=True)
                    score_data = []
                    for src, g in df.groupby("source"):
                        n = len(g)
                        p = (g["label"] == "Positif").sum()
                        ng = (g["label"] == "Negatif").sum()
                        nt = (g["label"] == "Netral").sum()
                        gss_src = round((p + 0.5 * nt) / n * 100, 1)
                        score_data.append({
                            "Channel": SOURCE_LABEL.get(src, src),
                            "Volume": n,
                            "Pos%": round(100 * p / n, 1),
                            "Neg%": round(100 * ng / n, 1),
                            "GSS": gss_src,
                        })
                    score_df = pd.DataFrame(score_data).sort_values("GSS", ascending=False)
                    st.dataframe(score_df, hide_index=True, use_container_width=True, height=160)

            # === ROW 3: Top Terms Negatif + Viral Detection ===
            r3c1, r3c2 = st.columns([1, 2])
            with r3c1:
                with st.container(border=True):
                    st.markdown(f'<div class="ss-card-title">{icon("clipboard", 18, ic.C_PRIMARY)} Top Terms Negatif</div><div class="ss-card-desc">Kata paling sering muncul di keluhan</div>', unsafe_allow_html=True)
                    neg_texts = df.loc[df["label"] == "Negatif", "text"].astype(str).tolist()
                    if len(neg_texts) >= 3:
                        terms = top_terms(neg_texts, 12, exclude=kw_terms)
                        if terms:
                            term_df = pd.DataFrame(terms, columns=["term", "count"])
                            fig_tt = px.bar(term_df, x="count", y="term", orientation="h",
                                color_discrete_sequence=["#e74c3c"])
                            fig_tt.update_layout(height=260, showlegend=False, margin=dict(t=5, b=5, l=5, r=5),
                                yaxis=dict(autorange="reversed"))
                            st.plotly_chart(fig_tt, use_container_width=True)
                    else:
                        st.info("Data negatif < 3.")

            with r3c2:
                with st.container(border=True):
                    st.markdown(f'<div class="ss-card-title">{icon("broadcast", 18, ic.C_PRIMARY)} Viral Detection</div><div class="ss-card-desc">Post dengan engagement tinggi — priority response</div>', unsafe_allow_html=True)
                    fig_scatter = px.scatter(df, x="score", y="likes", color="label", color_discrete_map=LABEL_COLOR,
                        hover_data=["source", "text", "kategori"], size="likes", size_max=30)
                    fig_scatter.update_layout(height=260, margin=dict(t=5, b=5, l=5, r=5),
                        xaxis_title="Skor Sentimen", yaxis_title="Engagement (Likes)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    st.plotly_chart(fig_scatter, use_container_width=True)

            # === Data Table + Download ===

            with st.expander("Data + Filter"):
                f1, f2, f3, f4 = st.columns(4)
                with f1:
                    sel_src = st.multiselect("Sumber", options=sorted(df["source"].unique()),
                        default=sorted(df["source"].unique()),
                        format_func=lambda s: SOURCE_LABEL.get(s, s), key="flt_src2")
                with f2:
                    sel_lab = st.multiselect("Sentimen", options=list(LABELS),
                        default=list(LABELS), key="flt_lab2")
                with f3:
                    if "kategori" in df.columns:
                        sel_cat = st.multiselect("Kategori", options=sorted(df["kategori"].unique()),
                            default=sorted(df["kategori"].unique()), key="flt_cat2")
                    else:
                        sel_cat = []
                with f4:
                    search_q = st.text_input("Cari teks", key="flt_search2", placeholder="keyword...")
                view = df.copy()
                if sel_src:
                    view = view[view["source"].isin(sel_src)]
                if sel_lab:
                    view = view[view["label"].isin(sel_lab)]
                if sel_cat and "kategori" in df.columns:
                    view = view[view["kategori"].isin(sel_cat)]
                if search_q:
                    view = view[view["text"].astype(str).str.contains(search_q, case=False, na=False)]
                view = view.sort_values(["likes"], ascending=False)
                st.caption(f"{len(view)} dari {len(df)} data")
                st.dataframe(view[["label","score","source","kategori","text","author","likes","url"]],
                    hide_index=True, use_container_width=True, height=250,
                    column_config={
                        "label": st.column_config.TextColumn("Sentimen"),
                        "score": st.column_config.NumberColumn("Skor", format="%.2f"),
                        "source": st.column_config.TextColumn("Sumber"),
                        "kategori": st.column_config.TextColumn("Kategori"),
                        "text": st.column_config.TextColumn("Teks", width="large"),
                        "author": st.column_config.TextColumn("Author"),
                        "likes": st.column_config.NumberColumn("Likes"),
                        "url": st.column_config.LinkColumn("buka", display_text="buka"),
                    })
                csv_bytes = df.to_csv(index=False, encoding="utf-8").encode("utf-8")
                fname = Path(st.session_state.get("out_csv", "hasil.csv")).name
                st.download_button("CSV", csv_bytes, file_name=fname, mime="text/csv", key="dl_csv2")

# ================================================ AI INSIGHT PANEL (conditional)
if _ai_area is not None:
    with _ai_area:
        st.subheader("AI Insight")

        df = st.session_state.get("df")
        meta = st.session_state.get("meta", {})

        if df is None or df.empty:
            st.warning("Jalankan analisis di tab Scrape dulu.")
        else:
            if st.button("Generate All AI Insights", type="primary", use_container_width=True, key="btn_all"):
                with st.spinner("Generating..."):
                    try:
                        st.session_state["ai_summary"] = generate_executive_summary(df, meta)
                    except Exception as e:
                        st.session_state["ai_summary"] = f"Gagal: {e}"
                    try:
                        st.session_state["ai_reco"] = generate_recommendations(df, meta)
                    except Exception as e:
                        st.session_state["ai_reco"] = f"Gagal: {e}"
                st.rerun()

            ai_summary = st.session_state.get("ai_summary")
            ai_reco = st.session_state.get("ai_reco")

            if ai_summary:
                with st.container(border=True):
                    st.markdown(f"<details open><summary>{icon('note', 14, ic.C_PRIMARY)} <b>Executive Summary</b></summary>{ai_summary}</details>", unsafe_allow_html=True)
            if ai_reco:
                with st.container(border=True):
                    st.markdown(f"<details open><summary>{icon('bulb', 14, ic.C_PRIMARY)} <b>Consideration & Reco</b></summary>{ai_reco}</details>", unsafe_allow_html=True)
            if not ai_summary and not ai_reco:
                st.info("Klik tombol di atas atau chat di bawah.")

            st.markdown("---")

            if "chat_messages" not in st.session_state:
                st.session_state["chat_messages"] = []

            kw_display = meta.get("keyword", "?")
            st.caption(f"{len(df)} data · keyword: {kw_display}")

            chat_container = st.container()
            with chat_container:
                for msg in st.session_state["chat_messages"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

            quick_prompts = {
                "Ringkasan sentimen": "Beri ringkasan singkat hasil sentiment ini.",
                "Kenapa banyak negatif?": "Analisis kenapa sentimen negatif tinggi. Keluhan utama?",
                "Rekomendasi": "Beri rekomendasi actionable berdasarkan hasil sentiment ini.",
                "Tren per sumber": "Bagaimana perbandingan sentimen antar sumber?",
            }
            _reset_sel = st.session_state.pop("_reset_quick", False)
            sel_prompt = st.selectbox("Quick prompt", options=list(quick_prompts.keys()),
                                       key="quick_sel", label_visibility="collapsed",
                                       index=None, placeholder="Pilih quick prompt...")
            if sel_prompt:
                st.session_state["pending_input"] = quick_prompts[sel_prompt]
                st.session_state["_reset_quick"] = True
                st.rerun()

            user_input = st.chat_input("Tanya tentang hasil...", key="chat_input")
            if "pending_input" in st.session_state:
                user_input = st.session_state.pop("pending_input")

            if user_input:
                st.session_state["chat_messages"].append({"role": "user", "content": user_input})
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(user_input)

                    context = build_sentiment_context(df, meta)
                    system_prompt = (
                        "Kamu adalah Sentiment Analysis Agent. "
                        "Jawab pertanyaan user tentang hasil sentiment berdasarkan context. "
                        "Aturan: (1) jawab dari data, (2) jangan mengarang, (3) actionable, "
                        "(4) Bahasa Indonesia natural.\n\n" + context
                    )
                    messages = [{"role": "system", "content": system_prompt}]
                    for msg in st.session_state["chat_messages"][-11:-1]:
                        messages.append({"role": msg["role"], "content": msg["content"]})
                    messages.append({"role": "user", "content": user_input})

                    with st.chat_message("assistant"):
                        with st.spinner("Menjawab..."):
                            try:
                                content, reasoning = chat_completion_sync(messages, temperature=0.4, max_tokens=2000)
                                if reasoning:
                                    with st.expander("💭 Reasoning", expanded=False):
                                        st.markdown(reasoning)
                                st.markdown(content)
                                response = content
                            except Exception as e:
                                response = f"Gagal: {e}"
                                st.error(response)
                    st.session_state["chat_messages"].append({"role": "assistant", "content": response})
                st.rerun()
