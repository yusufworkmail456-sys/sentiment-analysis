"""Page: Scrape & Analisis.

Two modes:
  1. Keyword-based scrape (existing) — scrape by keyword/hashtag across platforms
  2. URL-based scrape (new) — scrape comments from a single post URL
"""
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
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

    # ── Page head ───────────────────────────────────────────────────────
    chips = (ui.chip("auto_awesome", "Multi-platform", "info") +
             ui.chip("bolt", "6 Sumber Data", "gold") +
             ui.chip("link", "Scrape per URL", "ok"))
    st.markdown(ui.page_head(
        "Scrape & Analisis",
        "Kumpulkan komentar dari Instagram, YouTube, Web, Play Store, Facebook, "
        "dan TikTok. Analisis sentimen otomatis dengan model ID-Sentiment.",
        chips, ""), unsafe_allow_html=True)

    # ── Mode selector ────────────────────────────────────────────────────
    mode = st.tabs(["Scrape per Keyword", "Scrape per URL Postingan"])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1: KEYWORD MODE
    # ══════════════════════════════════════════════════════════════════════
    with mode[0]:
        _tab_keyword(_g)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2: URL MODE
    # ══════════════════════════════════════════════════════════════════════
    with mode[1]:
        _tab_url(_g)

    # ── Shared result section ───────────────────────────────────────────
    _show_results()


# ── Tab: Keyword ──────────────────────────────────────────────────────────
def _tab_keyword(_g):
    import core as _core
    from core import _load_ig_session

    # Credentials
    with st.expander("Kredensial Sumber Data", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            ig_sess = _load_ig_session()
            st.markdown(ui.source_tile("Instagram", "photo_camera",
                                       status_ok=check_session("instagram") == "ok",
                                       note="session_id"), unsafe_allow_html=True)
            ig_sid = st.text_input("IG session_id", key="ig_sid",
                                   value=ig_sess.get("session_id", ""),
                                   placeholder="session_id dari browser",
                                   label_visibility="collapsed")
            ig_user = st.text_input("IG username", key="ig_user",
                                    value=ig_sess.get("username", ""),
                                    placeholder="username",
                                    label_visibility="collapsed")
            ig_pwd = st.text_input("IG password", key="ig_pwd", type="password",
                                   placeholder="password",
                                   label_visibility="collapsed")
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
                    sf = Path(__file__).parent.parent / "ig_session.json"
                    if sf.exists():
                        sf.unlink()
                    save_session("instagram", data)
                    st.rerun()
                else:
                    st.error("Isi session_id atau username+password.")

        with c2:
            st.markdown(ui.source_tile("Facebook", "thumb_up",
                                       status_ok=check_session("facebook") == "ok",
                                       note="cookie c_user+xs"), unsafe_allow_html=True)
            fb_cookie = st.text_area("FB cookie", key="fb_cookie", height=60,
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
            st.markdown(ui.source_tile("TikTok", "music_note",
                                       status_ok=check_session("tiktok") == "ok",
                                       note="ms_token"), unsafe_allow_html=True)
            tt_token = st.text_input("TikTok ms_token", key="tt_token", type="password",
                                     placeholder="ms_token",
                                     label_visibility="collapsed")
            if st.button("Simpan TikTok", key="save_tt", use_container_width=True):
                if tt_token.strip():
                    ok, msg = test_tiktok(tt_token.strip())
                    if ok:
                        save_session("tiktok", {"ms_token": tt_token.strip()})
                        st.rerun()
                    else:
                        st.error(msg)

        with c3:
            st.markdown(ui.source_tile("YouTube", "play_circle",
                                       status_ok=True, note="tanpa login"), unsafe_allow_html=True)
            st.markdown(ui.source_tile("Web Berita", "language",
                                       status_ok=True, note="tanpa login"), unsafe_allow_html=True)
            st.markdown(ui.source_tile("Play Store", "shop",
                                       status_ok=True, note="tanpa login"), unsafe_allow_html=True)

    # Scrape config
    with st.expander("Konfigurasi Scrape", expanded=st.session_state.get("df") is None):
        p = st.pills("Contoh:", ["taspen", "pensiun", "asn", "taspen life"], key="kw_pills")
        if p and p != st.session_state.get("kw_applied"):
            st.session_state["kw_input"] = p
            st.session_state["kw_applied"] = p
        keyword = st.text_input(
            "Keyword", value="taspen", key="kw_input",
            label_visibility="collapsed",
            placeholder="nama brand, produk, atau topik")

        st.markdown('<div class="tsp-sb-label">Sumber &amp; jumlah target</div>',
                    unsafe_allow_html=True)
        SRC_CFG = [
            ("ig_on",  "n_ig",  "photo_camera", "Instagram",  300, 60),
            ("yt_on",  "n_yt",  "play_circle",  "YouTube",    300, 60),
            ("web_on", "n_web", "language",     "Web",         30,  8),
            ("ps_on",  "n_ps",  "shop",         "Play Store", 300, 60),
            ("fb_on",  "n_fb",  "thumb_up",     "Facebook",   300, 60),
            ("tt_on",  "n_tt",  "music_note",   "TikTok",     300, 60),
        ]
        scols = st.columns(6)
        src_vals = {}
        for col, (on_k, n_k, ic, label, mx, dv) in zip(scols, SRC_CFG):
            with col:
                st.markdown(ui.source_tile(label, ic), unsafe_allow_html=True)
                on = st.toggle("aktif", value=on_k in ("ig_on","yt_on","web_on","ps_on"),
                               key=on_k, label_visibility="collapsed")
                n  = st.number_input("max", 0, mx, dv, 10 if mx > 30 else 1,
                                     key=n_k, disabled=not on,
                                     label_visibility="collapsed")
                src_vals[on_k] = on
                src_vals[n_k]  = n

        ca1, ca2 = st.columns(2)
        with ca1:
            do_bot = st.toggle("Deteksi bot/spam", value=False, key="do_bot",
                               help="Tambah kolom is_bot_suspect berdasarkan heuristik username & teks")
        with ca2:
            do_ent = st.toggle("Tag entity mentions", value=False, key="do_ent",
                               help="Deteksi mention tokoh/lembaga terkait (Prabowo, BKN, dst)")

        run_scrape = st.button("Mulai Scrape + Analisis", type="primary",
                               use_container_width=True, key="run_kw")

    if run_scrape:
        if not keyword.strip():
            st.error("Keyword kosong.")
            return
        _execute_scrape(keyword, src_vals, do_bot, do_ent)


# ── Tab: URL ──────────────────────────────────────────────────────────────
def _tab_url(_g):
    st.markdown(ui.card(
        "Scrape per Postingan",
        "Input URL postingan → pilih platform → tentukan jumlah komentar",
        "", icon_name="link"), unsafe_allow_html=True)

    SOURCE_OPTIONS = {
        "Instagram": "instagram",
        "YouTube":   "youtube",
        "Play Store (App ID)": "playstore",
    }

    u1, u2, u3 = st.columns([3, 2, 1])
    with u1:
        url_input = st.text_input(
            "URL / ID Postingan",
            placeholder="https://www.instagram.com/p/... atau https://youtu.be/...",
            key="url_input")
    with u2:
        src_choice = st.selectbox(
            "Platform", options=list(SOURCE_OPTIONS.keys()), key="url_src")
    with u3:
        url_limit = st.number_input("Jumlah komentar", min_value=10,
                                    max_value=500, value=100, step=10,
                                    key="url_limit")

    # Extra options per platform
    if src_choice == "Instagram":
        st.caption(
            "Pastikan IG session_id sudah disimpan di tab Scrape per Keyword → Kredensial.")
    elif src_choice == "Play Store (App ID)":
        st.caption(
            "Masukkan package ID app (misal: com.taspen.mobile) atau URL Play Store.")

    url_do_bot = st.toggle("Deteksi bot/spam", value=False, key="url_do_bot")
    url_do_ent = st.toggle("Tag entity mentions", value=False, key="url_do_ent")

    run_url = st.button("Scrape URL + Analisis", type="primary",
                        use_container_width=True, key="run_url")

    if run_url:
        if not url_input.strip():
            st.error("URL/ID tidak boleh kosong.")
            return
        _execute_url_scrape(
            url_input.strip(),
            SOURCE_OPTIONS[src_choice],
            int(url_limit),
            url_do_bot,
            url_do_ent,
        )


def _execute_url_scrape(url: str, source: str, limit: int,
                        do_bot: bool, do_ent: bool):
    """Run scrape for a single post URL."""
    import core as _core

    logs, rows = [], []
    t0 = time.time()

    with st.status(f"Scraping {source} ({url[:60]}...)", expanded=True) as status:
        def log(msg):
            logs.append(msg)
            st.write(msg)

        try:
            if source == "instagram":
                from scrape import main as _ig_main  # noqa: F401
                # Use ig_web_scraper single-post approach
                from ig_web_scraper import _load_session_id, _make_session, _get_comments
                import re as _re
                sid, uname = _load_session_id()
                if not sid:
                    raise RuntimeError("IG session_id belum diset. "
                                       "Simpan dulu di tab Kredensial.")
                session = _make_session(sid, uname)
                # Extract post_id from URL
                shortcode = ""
                m = _re.search(r"/p/([A-Za-z0-9_-]+)", url)
                if m:
                    shortcode = m.group(1)
                if not shortcode:
                    raise RuntimeError(f"Tidak bisa ekstrak shortcode dari URL: {url}")
                # Get media pk from shortcode
                from instagrapi import Client
                cl = Client()
                media_pk = cl.media_pk_from_url(url)
                comments = _get_comments(session, str(media_pk),
                                         shortcode=shortcode,
                                         max_comments=limit, log=log)
                rows.extend(comments)
                log(f"IG: {len(rows)} komentar dari {url[:50]}")

            elif source == "youtube":
                from youtube_comment_downloader import (
                    YoutubeCommentDownloader, SORT_BY_RECENT)
                from datetime import datetime, timezone

                log(f"YT: ambil komentar dari {url[:60]} ...")
                dl = YoutubeCommentDownloader()
                count = 0
                for c in dl.get_comments_from_url(url, sort_by=SORT_BY_RECENT):
                    if count >= limit:
                        break
                    text = (c.get("text") or "").replace("\n", " ").strip()
                    if not text:
                        continue
                    tp = c.get("time_parsed")
                    if isinstance(tp, (int, float)) and tp:
                        date = datetime.fromtimestamp(tp, tz=timezone.utc).isoformat()
                    elif hasattr(tp, "isoformat"):
                        date = tp.isoformat()
                    else:
                        date = ""
                    rows.append({
                        "source": "youtube",
                        "text": text,
                        "author": c.get("author", "") or "",
                        "date": date,
                        "likes": c.get("votes", 0) or 0,
                        "url": url,
                    })
                    count += 1
                log(f"YT: {len(rows)} komentar")

            elif source == "playstore":
                from google_play_scraper import reviews, Sort
                # Accept full URL or just package ID
                import re as _re
                pkg_match = _re.search(r"id=([a-zA-Z0-9._]+)", url)
                pkg_id = pkg_match.group(1) if pkg_match else url.strip()
                log(f"Play Store: scrape reviews app {pkg_id} ...")
                result, _ = reviews(pkg_id, lang="id", country="id",
                                    sort=Sort.NEWEST, count=limit)
                for r in result:
                    text = (r.get("content") or "").strip().replace("\n", " ")
                    if len(text) < 5:
                        continue
                    rows.append({
                        "source": "playstore",
                        "text": text,
                        "author": r.get("userName", ""),
                        "date": r.get("at").isoformat() if r.get("at") else "",
                        "likes": r.get("thumbsUpCount", 0) or 0,
                        "url": f"https://play.google.com/store/apps/details?id={pkg_id}",
                    })
                log(f"Play Store: {len(rows)} reviews")

            else:
                raise RuntimeError(f"Platform '{source}' belum didukung untuk mode URL.")

        except Exception as e:
            log(f"GAGAL: {type(e).__name__}: {str(e)[:200]}")
            status.update(label="Scrape gagal", state="error")
            return

        if not rows:
            status.update(label="Tidak ada data", state="error")
            st.warning("Tidak ada komentar terkumpul.")
            return

        status.update(label=f"Selesai: {len(rows)} data", state="complete", expanded=False)

    # Sentiment analysis
    new_df = pd.DataFrame(rows)
    prog = st.progress(0.0, text="Analisis sentimen...")
    try:
        new_df = _core.run_sentiment(new_df, prog,
                                     detect_bots=do_bot, tag_entities=do_ent)
    finally:
        prog.empty()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    kw_label = source + "_url"
    out_csv = _core.OUT_DIR / f"sentiment_{kw_label}_{stamp}.csv"
    new_df.to_csv(out_csv, index=False, encoding="utf-8")

    st.session_state["df"]         = new_df
    st.session_state["out_csv"]    = str(out_csv)
    st.session_state["logs"]       = logs
    st.session_state["meta"]       = {
        "keyword": url[:80], "stamp": stamp,
        "durasi": round(time.time() - t0),
        "mode": "url", "source": source,
    }
    st.session_state["ai_summary"] = None
    st.session_state["ai_reco"]    = None
    st.rerun()


def _execute_scrape(keyword: str, src_vals: dict,
                    do_bot: bool, do_ent: bool):
    """Run keyword-based multi-source scrape."""
    import core as _core

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

        if src_vals["ig_on"]:  ambil("Instagram", scrape_ig,        src_vals["n_ig"])
        if src_vals["yt_on"]:  ambil("YouTube",   scrape_yt,        src_vals["n_yt"])
        if src_vals["web_on"]: ambil("Web",        scrape_web,       src_vals["n_web"])
        if src_vals["ps_on"]:  ambil("Play Store", scrape_playstore, src_vals["n_ps"])
        if src_vals["fb_on"]:  ambil("Facebook",   scrape_facebook,  src_vals["n_fb"])
        if src_vals["tt_on"]:  ambil("TikTok",     scrape_tiktok,    src_vals["n_tt"])

        rows = dedupe(rows)
        if not rows:
            status.update(label="Selesai – tidak ada data", state="error")
            st.error("Tidak ada data. Coba keyword lain atau aktifkan lebih banyak sumber.")
            return
        status.update(label=f"Scraping selesai: {len(rows)} baris",
                      state="complete", expanded=False)

    new_df = pd.DataFrame(rows)
    prog = st.progress(0.0, text="Menyiapkan model...")
    try:
        new_df = _core.run_sentiment(new_df, prog,
                                     detect_bots=do_bot, tag_entities=do_ent)
    finally:
        prog.empty()

    stamp   = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_csv = _core.OUT_DIR / f"sentiment_{keyword.strip().replace(' ','_')}_{stamp}.csv"
    new_df.to_csv(out_csv, index=False, encoding="utf-8")

    st.session_state["df"]         = new_df
    st.session_state["out_csv"]    = str(out_csv)
    st.session_state["logs"]       = logs
    st.session_state["meta"]       = {
        "keyword": keyword.strip(), "stamp": stamp,
        "durasi": round(time.time() - t0), "mode": "keyword",
    }
    st.session_state["ai_summary"] = None
    st.session_state["ai_reco"]    = None
    st.rerun()


# ── Shared result display ─────────────────────────────────────────────────
def _show_results():
    import re
    import core as _core

    df  = st.session_state.get("df")
    if df is None:
        st.markdown(ui.empty_state(
            "Belum ada data",
            "Atur kata kunci di tab Scrape per Keyword, atau input URL di tab Scrape per URL "
            "lalu klik tombol Mulai Scrape.", "radar"), unsafe_allow_html=True)
        return

    meta    = st.session_state.get("meta", {})
    out_csv = st.session_state.get("out_csv", "")

    df["likes"] = pd.to_numeric(df.get("likes"), errors="coerce").fillna(0).astype(int)
    if "keyakinan" not in df.columns:
        df["keyakinan"] = ["yakin" if s >= 0.6 else "ragu"
                           for s in pd.to_numeric(df["score"], errors="coerce").fillna(0)]
    if "kategori" not in df.columns:
        df = _core.classify_df(df)

    total = len(df)
    cnt   = df["label"].value_counts()
    pct   = {k: round(100 * cnt.get(k, 0) / total, 1) for k in _core.LABELS}
    skor  = round(pct["Positif"] - pct["Negatif"], 1)
    gss   = round((cnt.get("Positif", 0) + 0.5 * cnt.get("Netral", 0)) / total * 100, 1)
    kw_terms = set(re.findall(r"[a-zA-Zà-ÿ']{3,}", str(meta.get("keyword", "")).lower()))

    # KPI cards
    st.markdown(ui.stats_row([
        ui.stat("Total teks dianalisis", f"{total:,}",
                f"{df['source'].nunique()} sumber · {meta.get('keyword','?')}",
                "analytics", ui.NAVY),
        ui.stat("Net Sentiment Score", f"{skor:+.1f}",
                f"GSS {gss:.1f}/100", "sentiment_very_satisfied",
                ui.POS if skor >= 0 else ui.NEG),
        ui.stat("Rasio Positif", f"{pct['Positif']:.1f}%",
                f"{cnt.get('Positif', 0):,} komentar", "thumb_up", ui.NAVY),
        ui.stat("Negatif Alert", f"{pct['Negatif']:.1f}%",
                f"{cnt.get('Negatif', 0):,} komentar",
                "notification_important", ui.NEG),
    ]), unsafe_allow_html=True)

    # Distribusi + insight
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        st.markdown(ui.card(
            "Distribusi Sentimen", f"total {total:,} sample",
            ui.donut(pct, f"{skor:+.1f}", "Net Skor"),
            icon_name="pie_chart"), unsafe_allow_html=True)
    with cc2:
        bullets = _core.build_insights(df, exclude=kw_terms)
        st.markdown(ui.card(
            "Insight Otomatis", "temuan utama dari data",
            ui.insights_block(bullets) or
            '<div class="tsp-card-desc">Belum cukup data.</div>',
            icon_name="lightbulb"), unsafe_allow_html=True)

    # Bot & entity flags (if present)
    if "is_bot_suspect" in df.columns:
        bot_ct = df["is_bot_suspect"].sum()
        if bot_ct > 0:
            st.markdown(
                ui.alert_row([(
                    f"{ui.mt('bug_report',14)} {int(bot_ct)} akun terindikasi bot/spam",
                    "warn")]),
                unsafe_allow_html=True)

    if "entity_categories" in df.columns:
        ent_ct = (df["entity_categories"] != "").sum()
        if ent_ct > 0:
            top_ents = df[df["entity_categories"] != ""]["entity_categories"].value_counts().head(3)
            st.markdown(
                ui.alert_row([(
                    f"{ui.mt('account_tree',14)} {ent_ct} data mention entitas: "
                    + ", ".join(top_ents.index.tolist()),
                    "info")]),
                unsafe_allow_html=True)

    # Sample komentar
    with st.expander("Contoh komentar per label", expanded=False):
        for lab in _core.LABELS:
            sub = df[df["label"] == lab].sort_values("likes", ascending=False).head(2)
            if sub.empty:
                continue
            st.markdown(
                f'<div class="tsp-sb-label">{ui.esc(lab)} · {cnt.get(lab, 0)} data</div>',
                unsafe_allow_html=True)
            for _, r in sub.iterrows():
                warn = " · skor rendah" if r["keyakinan"] == "ragu" else ""
                st.markdown(ui.comment_card(
                    f"{_core.SOURCE_LABEL.get(r['source'], r['source'])} · "
                    f"{r.get('kategori', '?')}",
                    str(r["text"])[:220],
                    f"likes {r['likes']} · skor {r['score']}{warn}",
                    tone=ui.LABEL_COLOR.get(lab, ui.NEU)),
                    unsafe_allow_html=True)

    # Data table
    with st.expander("Data + Filter", expanded=False):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            sel_src = st.multiselect(
                "Sumber", options=sorted(df["source"].unique()),
                default=sorted(df["source"].unique()),
                format_func=lambda s: _core.SOURCE_LABEL.get(s, s), key="flt_src")
        with f2:
            sel_lab = st.multiselect("Sentimen", options=list(_core.LABELS),
                                     default=list(_core.LABELS), key="flt_lab")
        with f3:
            cats = sorted(df["kategori"].unique()) if "kategori" in df.columns else []
            sel_cat = st.multiselect("Kategori", options=cats,
                                     default=cats, key="flt_cat")
        with f4:
            search_q = st.text_input("Cari teks", key="flt_search",
                                     placeholder="keyword...")

        view = df.copy()
        if sel_src: view = view[view["source"].isin(sel_src)]
        if sel_lab: view = view[view["label"].isin(sel_lab)]
        if sel_cat and "kategori" in df.columns:
            view = view[view["kategori"].isin(sel_cat)]
        if search_q:
            view = view[view["text"].astype(str).str.contains(
                search_q, case=False, na=False)]
        view = view.sort_values(["likes"], ascending=False)

        st.caption(f"{len(view)} dari {len(df)} data")
        cols = [c for c in ["label", "score", "source", "kategori", "text",
                             "author", "likes", "url",
                             "is_bot_suspect", "entity_categories"]
                if c in view.columns]
        st.dataframe(view[cols], hide_index=True, use_container_width=True, height=260,
                     column_config={
                         "label":      st.column_config.TextColumn("Sentimen"),
                         "score":      st.column_config.NumberColumn("Skor", format="%.2f"),
                         "source":     st.column_config.TextColumn("Sumber"),
                         "kategori":   st.column_config.TextColumn("Kategori"),
                         "text":       st.column_config.TextColumn("Teks", width="large"),
                         "author":     st.column_config.TextColumn("Author"),
                         "likes":      st.column_config.NumberColumn("Likes"),
                         "url":        st.column_config.LinkColumn("buka", display_text="buka"),
                         "is_bot_suspect": st.column_config.CheckboxColumn("Bot?"),
                         "entity_categories": st.column_config.TextColumn("Entities"),
                     })
        csv_bytes = df.to_csv(index=False, encoding="utf-8").encode("utf-8")
        fname = Path(out_csv).name if out_csv else "hasil.csv"
        st.download_button("Unduh CSV", csv_bytes, file_name=fname, mime="text/csv")

    # Log
    with st.expander("Log proses", expanded=False):
        st.markdown(ui.terminal(st.session_state.get("logs", ["(kosong)"]),
                                "scrape log"), unsafe_allow_html=True)
