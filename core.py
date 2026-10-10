#!/usr/bin/env python3
"""Taspen Sentiment Platform - multi-platform sentiment analysis dashboard.

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
import httpx

# Optional Streamlit — only imported if running in Streamlit context
try:
    import streamlit as st
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

sys.path.insert(0, str(Path(__file__).parent))
from multiscrape import dedupe, scrape_ig, scrape_web, scrape_yt  # noqa: E402
from scrapers_extra import (  # noqa: E402
    scrape_facebook, scrape_tiktok, scrape_playstore,
    save_session, check_session, test_facebook, test_tiktok,
)
from categorize import classify_df, detect_bot_df, tag_entities_df  # noqa: E402
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
LABEL_COLOR = {"Positif": "#1e9e6a", "Netral": "#8aa5b5", "Negatif": "#d64545"}
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



# (Brand header lama dihapus — diganti tsp-topbar per page + st.logo sidebar)


# ----------------------------------------------------------------- model
def load_model():
    """Load (and cache) the sentiment pipeline. Works in both FastAPI and Streamlit."""
    if _HAS_ST:
        @st.cache_resource(show_spinner="Memuat model sentiment...")
        def _load():
            from transformers import pipeline
            return pipeline("text-classification", model=MODEL_NAME,
                            truncation=True, max_length=128, device=-1)
        return _load()
    # FastAPI: simple module-level cache
    if not hasattr(load_model, "_cache"):
        from transformers import pipeline
        load_model._cache = pipeline("text-classification", model=MODEL_NAME,
                                     truncation=True, max_length=128, device=-1)
    return load_model._cache


def run_sentiment(df, progress=None, detect_bots=False, tag_entities=False):
    """Run sentiment analysis.  progress can be a Streamlit progress bar or None."""
    clf = load_model()
    texts = df["text"].astype(str).tolist()
    labels, scores = [], []
    B = 16
    for i in range(0, len(texts), B):
        batch = texts[i:i + B]
        res = clf(batch)
        labels += [r["label"] for r in res]
        scores += [round(r["score"], 4) for r in res]
        if progress is not None and _HAS_ST:
            try:
                progress.progress(min(1.0, (i + B) / max(len(texts), 1)),
                                  text=f"Sentiment {min(i+B, len(texts))}/{len(texts)}")
            except Exception:
                pass
    df["label"] = [LABEL_ID.get(str(l).lower(), l) for l in labels]
    df["score"] = scores
    df["keyakinan"] = ["yakin" if s >= 0.6 else "ragu" for s in scores]
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = classify_df(df)
    if detect_bots:
        df = detect_bot_df(df)
    if tag_entities:
        df = tag_entities_df(df)
    # Normalisasi kolom opsional supaya JSON aman
    for opt in ("rating", "is_bot_suspect"):
        if opt in df.columns:
            df[opt] = df[opt].where(df[opt].notna(), None)
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
    return generate_executive_summary_from_context(context, meta)


def generate_executive_summary_from_context(context, meta):
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
    return generate_recommendations_from_context(context, meta)


def generate_recommendations_from_context(context, meta):
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
            orientation="h", marker_color="#1e9e6a"))
        fig.add_trace(go.Bar(name="Negatif %", y=list(absa_pct.index), x=(-absa_pct["Negatif"]).tolist(),
            orientation="h", marker_color="#d64545"))
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
        header=dict(values=list(score_df.columns), fill_color="#005d97", font=dict(color="white", size=12)),
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
    pdf.cell(0, 15, "Taspen Sentiment Platform — Report", new_x="LMARGIN", new_y="NEXT")
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
            import tempfile
            tmp_path = str(Path(tempfile.gettempdir()) / "chart_export.png")
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
    import tempfile
    out_path = str(Path(tempfile.gettempdir()) / "sentiment_report.pdf")
    pdf.output(out_path)
    with open(out_path, "rb") as f:
        return f.read()