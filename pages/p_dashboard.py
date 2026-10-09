"""Page: Dashboard - Visualization Overview.

Charts sit inside st.container(border=True) cards, restyled by app.py CSS
(.tsp-plotcard) so every plot is a real Taspen card.
"""
import streamlit as st


def _head(icon_svg, title, desc):
    st.markdown(
        f'<div class="tsp-card-head" style="--tsp-accent:#005d97;">'
        f'<span class="tsp-card-ic">{icon_svg}</span><div>'
        f'<div class="tsp-card-title">{title}</div>'
        f'<div class="tsp-card-desc">{desc}</div></div></div>',
        unsafe_allow_html=True)


def page_dashboard():
    from pages.header import topbar
    topbar("Dashboard", "Visualization overview hasil analisis sentimen gabungan semua sumber")

    import core as _core
    _g = globals()
    for _k, _v in vars(_core).items():
        if _k.startswith("__"):
            continue
        _g.setdefault(_k, _v)

    import ui

    df = st.session_state.get("df")
    if df is None or df.empty:
        st.markdown(ui.empty_state(
            "Belum ada data",
            "Jalankan scraping di halaman Scrape & Analisis dulu.",
            icon("radar", 30, ic.C_MUTED)), unsafe_allow_html=True)
        return

    tr1, tr2 = st.columns([4, 1])
    with tr2:
        export_pdf_btn = st.button("Export PDF", key="btn_pdf", use_container_width=True)

    total = len(df)
    cnt = df["label"].value_counts()
    pct = {k: round(100 * cnt.get(k, 0) / total, 1) for k in LABELS}
    skor = round(pct["Positif"] - pct["Negatif"], 1)
    gss = round((cnt.get("Positif", 0) + 0.5 * cnt.get("Netral", 0)) / total * 100, 1)
    df["likes"] = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0).astype(int)
    if "kategori" not in df.columns:
        df = classify_df(df)
    kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}",
                              str(st.session_state.get("meta", {}).get("keyword", "")).lower()))

    # === PDF Export ===
    if export_pdf_btn:
        with st.spinner("Generating PDF..."):
            try:
                pdf_bytes = export_pdf(df, st.session_state.get("meta", {}),
                                       st.session_state.get("ai_summary"),
                                       st.session_state.get("ai_reco"))
                st.download_button("Download PDF", pdf_bytes,
                                   file_name=f"sentiment_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                   mime="application/pdf", key="dl_pdf")
                st.success("PDF siap diunduh!")
            except Exception as e:
                st.error(f"PDF error: {e}")

    # === ALERT BADGES ===
    if "kategori" in df.columns and df["kategori"].notna().any():
        cat_tot = df.groupby("kategori").size()
        cat_neg = df[df["label"] == "Negatif"].groupby("kategori").size()
        cat_neg_pct = (cat_neg / cat_tot * 100).dropna()
        critical = cat_neg_pct[cat_neg_pct >= 50].sort_values(ascending=False)
        alerts = [(f"{cat}: {v:.0f}% negatif", "danger") for cat, v in critical.items()]
        if alerts:
            st.markdown(ui.alert_row(alerts), unsafe_allow_html=True)

    # === METRIC CARDS ===
    st.markdown(ui.stats_row([
        ui.stat("Total data", f"{total}", f"{df['source'].nunique()} sumber", ui.BLUE,
                icon("document", 15, ui.BLUE)),
        ui.stat("Positif", f"{pct['Positif']}%", f"{cnt.get('Positif', 0)} komentar",
                ui.POSITIF, icon("trend-up", 15, ui.POSITIF)),
        ui.stat("Netral", f"{pct['Netral']}%", f"{cnt.get('Netral', 0)} komentar",
                ui.NETRAL, icon("chart", 15, ui.NETRAL)),
        ui.stat("Negatif", f"{pct['Negatif']}%", f"{cnt.get('Negatif', 0)} komentar",
                ui.NEGATIF, icon("trend-down", 15, ui.NEGATIF)),
        ui.stat("GSS", f"{gss:.1f}", f"skor {skor:+.1f}", ui.GOLD_DARK,
                icon("gauge", 15, ui.GOLD_DARK)),
    ]), unsafe_allow_html=True)

    # === ROW 1: distribution bar + insights (custom cards) ===
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(ui.card("Distribusi sentimen", "proporsi tiap label",
                            ui.sentiment_bar(pct), accent=ui.BLUE,
                            icon_svg=icon("chart", 17, ui.BLUE)), unsafe_allow_html=True)
    with c2:
        insights_html = "".join(f'<div class="tsp-insight">{b}</div>'
                                for b in build_insights(df, exclude=kw_terms))
        st.markdown(ui.card("Insight otomatis", "temuan utama dari data",
                            insights_html or '<div class="tsp-card-desc">Belum cukup data.</div>',
                            accent=ui.GOLD_DARK,
                            icon_svg=icon("bulb", 17, ui.GOLD_DARK)), unsafe_allow_html=True)

    # === ROW 2: GSS Gauge + ABSA Diverging ===
    r1c1, r1c2 = st.columns([1, 2])
    with r1c1:
        with st.container(border=True):
            _head(icon("gauge", 18, ic.C_PRIMARY), "GSS Score", "Skor sentimen keseluruhan (0-100)")
            st.markdown(f"**{gss:.1f}/100** · Skor {skor:+.1f}")
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=gss,
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#005d97"},
                    "steps": [
                        {"range": [0, 40], "color": "#d64545"},
                        {"range": [40, 60], "color": "#e8a13a"},
                        {"range": [60, 80], "color": "#e8c21d"},
                        {"range": [80, 100], "color": "#1e9e6a"},
                    ],
                    "threshold": {"line": {"color": "#004a7c", "width": 3},
                                  "thickness": 0.75, "value": gss},
                }))
            fig_gauge.update_layout(height=210, margin=dict(t=10, b=5, l=10, r=10))
            st.plotly_chart(fig_gauge, use_container_width=True)

    with r1c2:
        with st.container(border=True):
            _head(icon("chart", 18, ic.C_PRIMARY), "Sentiment per Kategori",
                  "Persentase positif vs negatif per kategori domain")
            if "kategori" in df.columns and df["kategori"].notna().any():
                absa_data = df.groupby(["kategori", "label"]).size().unstack(fill_value=0)
                for lab in LABELS:
                    if lab not in absa_data.columns:
                        absa_data[lab] = 0
                absa_data = absa_data.reindex(columns=list(LABELS))
                absa_pct = absa_data.div(absa_data.sum(axis=1), axis=0) * 100
                fig_absa = go.Figure()
                fig_absa.add_trace(go.Bar(name="Positif %", y=list(absa_pct.index),
                                          x=absa_pct["Positif"].tolist(),
                                          orientation="h", marker_color="#1e9e6a"))
                fig_absa.add_trace(go.Bar(name="Negatif %", y=list(absa_pct.index),
                                          x=(-absa_pct["Negatif"]).tolist(),
                                          orientation="h", marker_color="#d64545"))
                fig_absa.update_layout(barmode="overlay", height=240,
                                       margin=dict(t=5, b=5, l=5, r=5),
                                       xaxis_title="% Sentiment", showlegend=True,
                                       xaxis=dict(tickformat=",.0f", range=[-100, 100]),
                                       legend=dict(orientation="h", yanchor="bottom",
                                                   y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_absa, use_container_width=True)
            else:
                st.info("Kolom kategori tidak tersedia.")

    # === ROW 3: Per Sumber + Channel Scorecard ===
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        with st.container(border=True):
            _head(icon("dashboard", 18, ic.C_PRIMARY), "Persebaran per Sumber",
                  "Komposisi sentimen tiap platform")
            src_data = df.groupby(["source", "label"]).size().unstack(fill_value=0)
            for lab in LABELS:
                if lab not in src_data.columns:
                    src_data[lab] = 0
            src_data = src_data.reindex(columns=list(LABELS))
            src_data.index = [SOURCE_LABEL.get(s, s) for s in src_data.index]
            fig_bar = go.Figure()
            for lab in LABELS:
                fig_bar.add_trace(go.Bar(name=lab, x=list(src_data.index),
                                         y=src_data[lab].tolist(),
                                         marker_color=LABEL_COLOR[lab]))
            fig_bar.update_layout(barmode="stack", height=240,
                                  margin=dict(t=5, b=5, l=5, r=5), showlegend=True,
                                  legend=dict(orientation="h", yanchor="bottom",
                                              y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_bar, use_container_width=True)

    with r2c2:
        with st.container(border=True):
            _head(icon("trophy", 18, ic.C_PRIMARY), "Channel Scorecard",
                  "Ranking platform berdasarkan GSS")
            score_data = []
            for src, g in df.groupby("source"):
                n = len(g)
                p = (g["label"] == "Positif").sum()
                ng = (g["label"] == "Negatif").sum()
                nt = (g["label"] == "Netral").sum()
                score_data.append({
                    "Channel": SOURCE_LABEL.get(src, src),
                    "Volume": n,
                    "Pos%": round(100 * p / n, 1),
                    "Neg%": round(100 * ng / n, 1),
                    "GSS": round((p + 0.5 * nt) / n * 100, 1),
                })
            score_df = pd.DataFrame(score_data).sort_values("GSS", ascending=False)
            score_df.insert(0, "", ["#" + str(i + 1) for i in range(len(score_df))])
            st.dataframe(score_df, hide_index=True, use_container_width=True, height=180)

    # === ROW 4: Top Terms Negatif + Viral Detection ===
    r3c1, r3c2 = st.columns([1, 2])
    with r3c1:
        with st.container(border=True):
            _head(icon("clipboard", 18, ic.C_PRIMARY), "Top Terms Negatif",
                  "Kata paling sering muncul di keluhan")
            neg_texts = df.loc[df["label"] == "Negatif", "text"].astype(str).tolist()
            if len(neg_texts) >= 3:
                terms = top_terms(neg_texts, 12, exclude=kw_terms)
                if terms:
                    term_df = pd.DataFrame(terms, columns=["term", "count"])
                    fig_tt = px.bar(term_df, x="count", y="term", orientation="h",
                                    color_discrete_sequence=["#d64545"])
                    fig_tt.update_layout(height=250, showlegend=False,
                                         margin=dict(t=5, b=5, l=5, r=5),
                                         yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_tt, use_container_width=True)
            else:
                st.info("Data negatif < 3.")

    with r3c2:
        with st.container(border=True):
            _head(icon("broadcast", 18, ic.C_PRIMARY), "Viral Detection",
                  "Post dengan engagement tinggi - priority response")
            fig_scatter = px.scatter(df, x="score", y="likes", color="label",
                                     color_discrete_map=LABEL_COLOR,
                                     hover_data=["source", "text", "kategori"],
                                     size="likes", size_max=30)
            fig_scatter.update_layout(height=250, margin=dict(t=5, b=5, l=5, r=5),
                                      xaxis_title="Skor Sentimen",
                                      yaxis_title="Engagement (Likes)",
                                      legend=dict(orientation="h", yanchor="bottom",
                                                  y=1.02, xanchor="right", x=1))
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
        cols = [c for c in ["label", "score", "source", "kategori", "text", "author", "likes", "url"]
                if c in view.columns]
        st.dataframe(view[cols], hide_index=True, use_container_width=True, height=250,
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
