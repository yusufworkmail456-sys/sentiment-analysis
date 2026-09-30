#!/usr/bin/env python3
"""Streamlit UI: Sentiment Analysis Taspen — compact 2-column layout.

Left:  Tabs [Scrape & Analisis (incl. credential mgmt), Dashboard]
Right: AI Insight (exec summary + reco + chatbot) — sticky

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
from taspen_categorize import classify_df  # noqa: E402
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

MODEL_NAME = "w11wo/indonesian-roberta-base-sentiment-classifier"
OUT_DIR = Path(__file__).parent / "hasil"
OUT_DIR.mkdir(exist_ok=True)

LLM_BASE_URL = "https://9router.amital.co.id/v1"
LLM_MODEL = "coding"


def _get_llm_key():
    env_path = "/root/.hermes/.env"
    key_name = "HERMES_CUSTOM_9ROUTER_AMITAL_CO_ID_API_KEY"
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key_name}=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get(key_name, "")


LLM_API_KEY = _get_llm_key()


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
TASPEN_STOPWORDS = {
    "taspen", "pensun", "pensiun", "pns", "asn", "pegawai", "negeri",
    "sipil", "badan", "usaha", "milik", "negara", "bumn",
}
FONT_PATH = str(Path(__file__).parent / "assets" / "fonts" / "DejaVuSans.ttf")

st.set_page_config(page_title="Sentiment Taspen", layout="wide")

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
        f"=== KONTEKS SENTIMENT TASPEN ===",
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
        return data["choices"][0]["message"]["content"]


def generate_executive_summary(df, meta):
    context = build_sentiment_context(df, meta)
    messages = [
        {"role": "system", "content": (
            "Kamu adalah Senior Sentiment Analyst untuk PT Taspen (Persero). "
            "Buat EXECUTIVE SUMMARY untuk manajemen senior. "
            "Format: 2-3 paragraf, bahasa Indonesia formal-profesional. "
            "Struktur: (1) Ringkasan temuan + skor, (2) Kategori/area perlu perhatian, "
            "(3) Catatan kualitas data. Jangan mengarang data. Hanya dari context."
        )},
        {"role": "user", "content": f"{context}\n\nBuat executive summary."},
    ]
    return chat_completion_sync(messages, temperature=0.3, max_tokens=800)


def generate_recommendations(df, meta):
    context = build_sentiment_context(df, meta)
    messages = [
        {"role": "system", "content": (
            "Kamu adalah Strategic Advisor untuk PT Taspen (Persero). "
            "Buat CONSIDERATION & RECOMMENDATION dari hasil sentiment. "
            "Format Bahasa Indonesia:\n## Consideration\n- 3-5 poin strategis\n"
            "## Recommendation\n- 3-5 rekomendasi actionable (specific, time-bound)\n"
            "Hanya dari data. Jangan mengarang."
        )},
        {"role": "user", "content": f"{context}\n\nBuat consideration & recommendation."},
    ]
    return chat_completion_sync(messages, temperature=0.4, max_tokens=1200)




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
    pdf.add_font("DejaVu", "", "/root/ig-sentiment/assets/fonts/DejaVuSans.ttf")
    pdf.add_font("DejaVu", "B", "/root/ig-sentiment/assets/fonts/DejaVuSans-Bold.ttf")

    # Cover page
    pdf.add_page()
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 15, "Sentiment Analysis Report - Taspen", new_x="LMARGIN", new_y="NEXT")
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
st.markdown(f'<div style="display:flex;align-items:center;gap:8px;">{icon("chart", 28, ic.C_PRIMARY)}<h1 style="margin:0;">Sentiment Analysis — Taspen</h1></div>', unsafe_allow_html=True)
st.caption("Multi-platform · IndoBERT · Taspen categorization · AI insight")

# AI panel visibility: hidden (default) → narrow → wide
_ai_state = st.session_state.get("ai_state", "hidden")  # hidden | narrow | wide
_ai_btn_label = {"hidden": "AI", "narrow": "AI ⤢", "wide": "AI ⤡"}[_ai_state]

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
                ig_user_val = ig_sess.get("username", "")
                ig_user = st.text_input("IG username", key="ig_user", value=ig_user_val, label_visibility="collapsed", placeholder="IG username")
                ig_pwd = st.text_input("IG password", type="password", key="ig_pwd", label_visibility="collapsed", placeholder="IG password")
                if st.button("Simpan IG", key="save_ig", help="Simpan & login IG"):
                    if ig_user.strip() and ig_pwd:
                        save_session("instagram", {"username": ig_user.strip(), "password": ig_pwd})
                        os.environ["IG_USER"] = ig_user.strip()
                        os.environ["IG_PASS"] = ig_pwd
                        st.rerun()
                    else:
                        st.error("Username dan password wajib diisi.")

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
                st.caption("Play Store & Web: tanpa login. Review app Andal/TASPEN Mobile/TASPEN Life otomatis.")

        # --- Config & Run ---
        with st.expander("Konfigurasi", expanded=df is None):
            p = st.pills("Contoh:", ["taspen", "klaim taspen", "dapen online", "pensiun pns"], key="kw_pills")
            if p and p != st.session_state.get("kw_applied"):
                st.session_state["kw_input"] = p
                st.session_state["kw_applied"] = p

            keyword = st.text_input("Keyword", value="taspen", key="kw_input",
                                    help="Contoh: taspen, klaim taspen, dapen online")

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
                    st.markdown(f"- {b}")

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
                        "url": st.column_config.LinkColumn("buka", display_text="↗"),
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
                    st.markdown(f'<div class="ss-card-title">{icon("chart", 18, ic.C_PRIMARY)} Sentiment per Kategori</div><div class="ss-card-desc">Persentase positif vs negatif per kategori Taspen</div>', unsafe_allow_html=True)
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

            with st.expander("🗂️ Data + Filter"):
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
                        "url": st.column_config.LinkColumn("buka", display_text="↗"),
                    })
                csv_bytes = df.to_csv(index=False, encoding="utf-8").encode("utf-8")
                fname = Path(st.session_state.get("out_csv", "hasil.csv")).name
                st.download_button("⬇️ CSV", csv_bytes, file_name=fname, mime="text/csv", key="dl_csv2")

# ================================================ AI INSIGHT PANEL (conditional)
if _ai_area is not None:
    with _ai_area:
        st.subheader("🤖 AI Insight")

        df = st.session_state.get("df")
        meta = st.session_state.get("meta", {})

        if df is None or df.empty:
            st.warning("⚠️ Jalankan analisis di tab Scrape dulu.")
        else:
            if st.button("🚀 Generate All AI Insights", type="primary", use_container_width=True, key="btn_all"):
                with st.spinner("🤔 Generating..."):
                    try:
                        st.session_state["ai_summary"] = generate_executive_summary(df, meta)
                    except Exception as e:
                        st.session_state["ai_summary"] = f"❌ {e}"
                    try:
                        st.session_state["ai_reco"] = generate_recommendations(df, meta)
                    except Exception as e:
                        st.session_state["ai_reco"] = f"❌ {e}"
                st.rerun()

            ai_summary = st.session_state.get("ai_summary")
            ai_reco = st.session_state.get("ai_reco")

            if ai_summary:
                with st.container(border=True):
                    st.markdown(f"<details open><summary>📝 <b>Executive Summary</b></summary>{ai_summary}</details>", unsafe_allow_html=True)
            if ai_reco:
                with st.container(border=True):
                    st.markdown(f"<details open><summary>💡 <b>Consideration & Reco</b></summary>{ai_reco}</details>", unsafe_allow_html=True)
            if not ai_summary and not ai_reco:
                st.info("👆 Klik tombol di atas atau chat di bawah.")

            st.markdown("---")

            if "chat_messages" not in st.session_state:
                st.session_state["chat_messages"] = []

            kw_display = meta.get("keyword", "?")
            st.caption(f"✅ {len(df)} data · keyword: {kw_display}")

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
                        "Kamu Sentiment Analysis Agent untuk PT Taspen (Persero). "
                        "Jawab pertanyaan user tentang hasil sentiment berdasarkan context. "
                        "Aturan: (1) jawab dari data, (2) jangan mengarang, (3) actionable, "
                        "(4) Bahasa Indonesia natural.\n\n" + context
                    )
                    messages = [{"role": "system", "content": system_prompt}]
                    for msg in st.session_state["chat_messages"][-11:-1]:
                        messages.append({"role": msg["role"], "content": msg["content"]})
                    messages.append({"role": "user", "content": user_input})

                    with st.chat_message("assistant"):
                        with st.spinner("🤔"):
                            try:
                                response = chat_completion_sync(messages, temperature=0.4, max_tokens=2000)
                                st.markdown(response)
                            except Exception as e:
                                response = f"❌ {e}"
                                st.error(response)
                    st.session_state["chat_messages"].append({"role": "assistant", "content": response})
                st.rerun()
