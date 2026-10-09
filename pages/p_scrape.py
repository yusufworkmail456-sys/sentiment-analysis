"""Page: Scrape & Analisis - keyword + kredensial + hasil."""
import streamlit as st

def page_scrape():
    from pages.header import topbar
    topbar("Scrape & Analisis", "Kumpulkan data dari 6 platform lalu analisis sentimennya")
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
