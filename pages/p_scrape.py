"""Page: Scrape & Analisis - konfigurasi + kredensial + hasil (full custom UI)."""
import streamlit as st
import ui


def page_scrape():
    from pages.header import topbar
    import core as _core
    _g = globals()
    for _k, _v in vars(_core).items():
        if not _k.startswith("__"):
            _g.setdefault(_k, _v)
    from core import _load_ig_session
    _g["_load_ig_session"] = _load_ig_session

    topbar("Scrape & Analisis",
           "Kumpulkan data dari 6 platform lalu analisis sentimennya")

    df = st.session_state.get("df")

    # ============================================ 1. KREDENSIAL (kartu custom)
    with st.expander("Kredensial Sumber Data", expanded=False):
        def _tile(icon_name, label, plat, note=""):
            ok = plat in ("youtube", "web", "playstore") or check_session(plat) == "ok"
            return ui.source_tile(None, label, icon(icon_name, 16, ic.C_PRIMARY),
                                  ic.C_PRIMARY, status_ok=ok, note=note)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(_tile("instagram", "Instagram", "instagram", "session_id"),
                        unsafe_allow_html=True)
            ig_sess = _load_ig_session()
            ig_sid = st.text_input("IG session_id", key="ig_sid",
                                   value=ig_sess.get("session_id", ""),
                                   placeholder="session_id dari browser",
                                   label_visibility="collapsed")
            ig_user = st.text_input("IG username", key="ig_user",
                                    value=ig_sess.get("username", ""),
                                    placeholder="username", label_visibility="collapsed")
            ig_pwd = st.text_input("IG password", key="ig_pwd", type="password",
                                   placeholder="password", label_visibility="collapsed")
            if st.button("Simpan IG", key="save_ig", use_container_width=True):
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
                    from pathlib import Path as _P
                    _sf = _P(__file__).parent.parent / "ig_session.json"
                    if _sf.exists():
                        _sf.unlink()
                    save_session("instagram", data)
                    st.rerun()
                else:
                    st.error("Isi session_id atau username+password.")

        with c2:
            st.markdown(_tile("facebook", "Facebook", "facebook", "cookie c_user+xs"),
                        unsafe_allow_html=True)
            fb_cookie = st.text_area("FB cookie", key="fb_cookie", height=68,
                                     placeholder="Paste cookie (c_user=...; xs=...)",
                                     label_visibility="collapsed")
            if st.button("Simpan FB", key="save_fb", use_container_width=True):
                if fb_cookie.strip():
                    ok, msg = test_facebook(fb_cookie.strip())
                    if ok:
                        save_session("facebook", {"cookie": fb_cookie.strip()})
                        st.rerun()
                    else:
                        st.error(msg)
            st.markdown(_tile("tiktok", "TikTok", "tiktok", "ms_token"),
                        unsafe_allow_html=True)
            tt_token = st.text_input("TikTok ms_token", key="tt_token", type="password",
                                     placeholder="ms_token", label_visibility="collapsed")
            if st.button("Simpan TikTok", key="save_tt", use_container_width=True):
                if tt_token.strip():
                    ok, msg = test_tiktok(tt_token.strip())
                    if ok:
                        save_session("tiktok", {"ms_token": tt_token.strip()})
                        st.rerun()
                    else:
                        st.error(msg)

        with c3:
            st.markdown(_tile("youtube", "YouTube", "youtube", "tanpa login"), unsafe_allow_html=True)
            st.markdown(_tile("web", "Web berita", "web", "tanpa login"), unsafe_allow_html=True)
            st.markdown(_tile("playstore", "Play Store", "playstore", "tanpa login"),
                        unsafe_allow_html=True)

    # ============================================ 2. KONFIGURASI SCRAPE
    with st.expander("Konfigurasi", expanded=df is None):
        st.markdown(ui.section("Kata kunci", "topik yang dicari di semua platform", 1),
                    unsafe_allow_html=True)
        p = st.pills("Contoh:", ["taspen", "pensiun", "asn", "taspen life"], key="kw_pills")
        if p and p != st.session_state.get("kw_applied"):
            st.session_state["kw_input"] = p
            st.session_state["kw_applied"] = p
        keyword = st.text_input("Keyword", value="taspen", key="kw_input",
                                label_visibility="collapsed",
                                placeholder="nama brand, produk, atau topik")

        st.markdown(ui.section("Sumber & jumlah", "aktifkan platform, atur target data", 2),
                    unsafe_allow_html=True)
        # Tile per source + toggle + jumlah, dalam grid 6 kolom
        SRC_CFG = [
            ("ig_on", "n_ig", "instagram", "Instagram", 300, 60),
            ("yt_on", "n_yt", "youtube", "YouTube", 300, 60),
            ("web_on", "n_web", "web", "Web", 30, 8),
            ("ps_on", "n_ps", "playstore", "Play Store", 300, 60),
            ("fb_on", "n_fb", "facebook", "Facebook", 300, 60),
            ("tt_on", "n_tt", "tiktok", "TikTok", 300, 60),
        ]
        scols = st.columns(6)
        src_vals = {}
        for col, (on_k, n_k, ic_name, label, mx, dv) in zip(scols, SRC_CFG):
            with col:
                default_on = on_k in ("ig_on", "yt_on", "web_on", "ps_on")
                on = st.toggle(label, value=default_on, key=on_k)
                n = st.number_input("max", 0, mx, dv, 10 if mx > 30 else 1, key=n_k,
                                    disabled=not on, label_visibility="collapsed")
                src_vals[on_k] = on
                src_vals[n_k] = n

        run_scrape = st.button("Mulai Scrape + Analisis", type="primary",
                               use_container_width=True)

    if run_scrape:
        if not keyword.strip():
            st.error("Keyword kosong.")
        else:
            logs, rows = [], []
            t0 = time.time()
            with st.status("Scraping...", expanded=True) as status:
                def log(msg):
                    logs.append(msg)
                    st.write(msg)

                def ambil(nama, fn, n):
                    if n <= 0:
                        return
                    log(f"> {nama}: mulai (target {n})...")
                    try:
                        got = fn(keyword.strip(), n, log)
                        rows.extend(got)
                        log(f"OK {nama}: {len(got)} baris")
                    except Exception as e:
                        log(f"FAIL {nama}: {type(e).__name__} {str(e)[:120]}")

                if src_vals["ig_on"]: ambil("Instagram", scrape_ig, src_vals["n_ig"])
                if src_vals["yt_on"]: ambil("YouTube", scrape_yt, src_vals["n_yt"])
                if src_vals["web_on"]: ambil("Web", scrape_web, src_vals["n_web"])
                if src_vals["ps_on"]: ambil("Play Store", scrape_playstore, src_vals["n_ps"])
                if src_vals["fb_on"]: ambil("Facebook", scrape_facebook, src_vals["n_fb"])
                if src_vals["tt_on"]: ambil("TikTok", scrape_tiktok, src_vals["n_tt"])

                rows = dedupe(rows)
                if not rows:
                    status.update(label="Selesai — tidak ada data", state="error")
                    st.error("Tidak ada data. Coba keyword lain.")
                    rows = None
                else:
                    status.update(label=f"Scraping selesai: {len(rows)} baris",
                                  state="complete", expanded=False)

            if rows:
                new_df = pd.DataFrame(rows)
                progress = st.progress(0.0, text="Menyiapkan model...")
                try:
                    new_df = run_sentiment(new_df, progress)
                finally:
                    progress.empty()
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                out_csv = OUT_DIR / f"sentiment_{keyword.strip().replace(' ', '_')}_{stamp}.csv"
                new_df.to_csv(out_csv, index=False, encoding="utf-8")
                st.session_state["df"] = new_df
                st.session_state["out_csv"] = str(out_csv)
                st.session_state["logs"] = logs
                st.session_state["meta"] = {"keyword": keyword.strip(), "stamp": stamp,
                                            "durasi": round(time.time() - t0)}
                st.session_state["ai_summary"] = None
                st.session_state["ai_reco"] = None
                st.rerun()

    # ============================================ 3. HASIL
    df = st.session_state.get("df")
    if df is None:
        st.markdown(ui.empty_state(
            "Belum ada data",
            "Atur kata kunci dan sumber di panel Konfigurasi, lalu klik Mulai Scrape + Analisis.",
            icon("radar", 30, ic.C_MUTED)), unsafe_allow_html=True)
        return

    meta = st.session_state.get("meta", {})
    out_csv = st.session_state.get("out_csv", "")
    kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}", str(meta.get("keyword", "")).lower()))
    df["likes"] = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0).astype(int)
    if "keyakinan" not in df.columns:
        df["keyakinan"] = ["yakin" if s >= 0.6 else "ragu"
                           for s in pd.to_numeric(df["score"], errors="coerce").fillna(0)]
    if "kategori" not in df.columns:
        df = classify_df(df)

    total = len(df)
    cnt = df["label"].value_counts()
    pct = {k: round(100 * cnt.get(k, 0) / total, 1) for k in LABELS}
    skor = round(pct["Positif"] - pct["Negatif"], 1)
    gss = round((cnt.get("Positif", 0) + 0.5 * cnt.get("Netral", 0)) / total * 100, 1)

    st.markdown(ui.section("Hasil analisis", f"kata kunci: {meta.get('keyword','?')}", 3),
                unsafe_allow_html=True)

    # --- stat cards custom (bukan st.metric)
    st.markdown(ui.stats_row([
        ui.stat("Total data", f"{total}", f"{len(df['source'].unique())} sumber", ui.BLUE,
                icon("document", 15, ui.BLUE)),
        ui.stat("Positif", f"{pct['Positif']}%", f"{cnt.get('Positif',0)} komentar",
                ui.POSITIF, icon("trend-up", 15, ui.POSITIF)),
        ui.stat("Netral", f"{pct['Netral']}%", f"{cnt.get('Netral',0)} komentar",
                ui.NETRAL, icon("chart", 15, ui.NETRAL)),
        ui.stat("Negatif", f"{pct['Negatif']}%", f"{cnt.get('Negatif',0)} komentar",
                ui.NEGATIF, icon("trend-down", 15, ui.NEGATIF)),
        ui.stat("GSS", f"{gss:.1f}", f"skor {skor:+.1f}", ui.GOLD_DARK,
                icon("gauge", 15, ui.GOLD_DARK)),
    ]), unsafe_allow_html=True)

    # --- distribution bar + insights, side by side dalam kartu
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        st.markdown(ui.card(
            "Distribusi sentimen", "proporsi tiap label",
            ui.sentiment_bar(pct), accent=ui.BLUE,
            icon_svg=icon("chart", 17, ui.BLUE)), unsafe_allow_html=True)
    with cc2:
        insights_html = "".join(f'<div class="tsp-insight">{b}</div>'
                                for b in build_insights(df, exclude=kw_terms))
        st.markdown(ui.card(
            "Insight otomatis", "temuan utama dari data",
            insights_html, accent=ui.GOLD_DARK,
            icon_svg=icon("bulb", 17, ui.GOLD_DARK)), unsafe_allow_html=True)

    # --- contoh komentar per label (custom quote cards)
    with st.expander("Contoh komentar per label", expanded=False):
        for lab in LABELS:
            sub = df[df["label"] == lab].sort_values("likes", ascending=False).head(2)
            if sub.empty:
                continue
            st.markdown(ui.section(f"{lab} ({cnt.get(lab,0)})", "", None),
                        unsafe_allow_html=True)
            for _, r in sub.iterrows():
                warn = " · skor rendah" if r["keyakinan"] == "ragu" else ""
                st.markdown(ui.comment_card(
                    f"{SOURCE_LABEL.get(r['source'], r['source'])} · {r.get('kategori','?')}",
                    str(r["text"])[:220],
                    f"likes {r['likes']} · skor {r['score']}{warn}",
                    tone=ui.LABEL_COLOR.get(lab, ui.NETRAL)), unsafe_allow_html=True)

    # --- data + filter
    with st.expander("Data + Filter", expanded=False):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            sel_src = st.multiselect("Sumber", options=sorted(df["source"].unique()),
                                     default=sorted(df["source"].unique()),
                                     format_func=lambda s: SOURCE_LABEL.get(s, s), key="flt_src")
        with f2:
            sel_lab = st.multiselect("Sentimen", options=list(LABELS),
                                     default=list(LABELS), key="flt_lab")
        with f3:
            sel_cat = st.multiselect("Kategori", options=sorted(df["kategori"].unique()),
                                     default=sorted(df["kategori"].unique()), key="flt_cat")
        with f4:
            search_q = st.text_input("Cari teks", key="flt_search", placeholder="keyword...")

        view = df.copy()
        if sel_src:
            view = view[view["source"].isin(sel_src)]
        if sel_lab:
            view = view[view["label"].isin(sel_lab)]
        if sel_cat:
            view = view[view["kategori"].isin(sel_cat)]
        if search_q:
            view = view[view["text"].astype(str).str.contains(search_q, case=False, na=False)]
        view = view.sort_values(["likes"], ascending=False)

        st.caption(f"{len(view)} dari {len(df)} data")
        st.dataframe(view[["label", "score", "source", "kategori", "text", "author", "likes", "url"]],
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
        st.download_button("Unduh CSV", csv_bytes, file_name=fname, mime="text/csv")

    # --- log: terminal custom
    with st.expander("Log proses", expanded=False):
        st.markdown(ui.terminal(st.session_state.get("logs", ["(kosong)"]),
                                "scrape log"), unsafe_allow_html=True)
