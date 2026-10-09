"""Page: AI Insight - exec summary, recommendations, chatbot (custom UI)."""
import streamlit as st


def page_ai():
    from pages.header import topbar
    topbar("AI Insight", "Ringkasan eksekutif, rekomendasi, dan chatbot analisis")

    import core as _core
    _g = globals()
    for _k, _v in vars(_core).items():
        if _k.startswith("__"):
            continue
        _g.setdefault(_k, _v)

    import ui

    df = st.session_state.get("df")
    meta = st.session_state.get("meta", {})

    if df is None or df.empty:
        st.markdown(ui.empty_state(
            "Belum ada data",
            "Jalankan analisis di halaman Scrape & Analisis dulu.",
            icon("ai", 30, ic.C_MUTED)), unsafe_allow_html=True)
        return

    # ===== generate button =====
    btn_c1, btn_c2 = st.columns([3, 1])
    with btn_c1:
        st.markdown(
            '<div class="tsp-aiintro">Analisis otomatis oleh Taspen Sentiment Platform '
            'Analysis Agent atas data terbaru.</div>', unsafe_allow_html=True)
    with btn_c2:
        gen_btn = st.button("Generate AI Insights", type="primary",
                            use_container_width=True, key="btn_all")

    if gen_btn:
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
        st.markdown(ui.card(
            "Executive Summary", "ringkasan hasil analisis terkini",
            f'<div class="tsp-md">{ai_summary}</div>', accent=ui.BLUE,
            icon_svg=icon("note", 17, ui.BLUE)), unsafe_allow_html=True)
    if ai_reco:
        st.markdown(ui.card(
            "Consideration & Rekomendasi", "langkah yang disarankan",
            f'<div class="tsp-md">{ai_reco}</div>', accent=ui.GOLD_DARK,
            icon_svg=icon("bulb", 17, ui.GOLD_DARK)), unsafe_allow_html=True)
    if not ai_summary and not ai_reco:
        st.markdown(ui.empty_state(
            "Belum ada insight",
            "Klik Generate AI Insights, atau tanya lewat chat di bawah.",
            icon("sparkle", 28, ic.C_MUTED)), unsafe_allow_html=True)

    # ===== chatbot =====
    st.markdown(ui.section("Tanya jawab", "chat dengan analysis agent", None),
                unsafe_allow_html=True)
    st.caption(f"{len(df)} data · keyword: {meta.get('keyword', '?')}")

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    quick_prompts = {
        "Ringkasan sentimen": "Beri ringkasan singkat hasil sentiment ini.",
        "Kenapa banyak negatif?": "Analisis kenapa sentimen negatif tinggi. Keluhan utama?",
        "Rekomendasi": "Beri rekomendasi actionable berdasarkan hasil sentiment ini.",
        "Tren per sumber": "Bagaimana perbandingan sentimen antar sumber?",
    }
    st.session_state.pop("_reset_quick", None)
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

    # render history as custom bubbles
    for msg in st.session_state["chat_messages"]:
        if msg["role"] == "user":
            st.markdown(f'<div class="tsp-chat-row"><div class="tsp-chat-user">'
                        f'{ui.esc(msg["content"])}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="tsp-chat-row"><div class="tsp-chat-ai">'
                        f'<div class="tsp-chat-ai-head">{icon("ai", 13, ui.BLUE)} '
                        f'Analysis Agent</div>'
                        f'<div class="tsp-md">{msg["content"]}</div></div></div>',
                        unsafe_allow_html=True)

    if user_input:
        st.session_state["chat_messages"].append({"role": "user", "content": user_input})
        st.markdown(f'<div class="tsp-chat-row"><div class="tsp-chat-user">'
                    f'{ui.esc(user_input)}</div></div>', unsafe_allow_html=True)

        context = build_sentiment_context(df, meta)
        system_prompt = (
            "Kamu adalah Taspen Sentiment Platform Analysis Agent. "
            "Jawab pertanyaan user tentang hasil sentiment berdasarkan context. "
            "Aturan: (1) jawab dari data, (2) jangan mengarang, (3) actionable, "
            "(4) Bahasa Indonesia natural.\n\n" + context
        )
        messages = [{"role": "system", "content": system_prompt}]
        for msg in st.session_state["chat_messages"][-11:-1]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_input})

        with st.spinner("Menjawab..."):
            try:
                content, reasoning = chat_completion_sync(messages, temperature=0.4, max_tokens=2000)
            except Exception as e:
                content, reasoning = f"Gagal: {e}", None
        if reasoning:
            with st.expander("Reasoning", expanded=False):
                st.markdown(reasoning)
        st.markdown(f'<div class="tsp-chat-row"><div class="tsp-chat-ai">'
                    f'<div class="tsp-chat-ai-head">{icon("ai", 13, ui.BLUE)} '
                    f'Analysis Agent</div>'
                    f'<div class="tsp-md">{content}</div></div></div>',
                    unsafe_allow_html=True)
        st.session_state["chat_messages"].append({"role": "assistant", "content": content})
        st.rerun()
