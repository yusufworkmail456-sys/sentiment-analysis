"""Page: AI Insight - exec summary, recommendations, chatbot."""
import streamlit as st

def page_ai():
    from pages.header import topbar
    topbar("AI Insight", "Ringkasan eksekutif, rekomendasi, dan chatbot analisis")
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
                    "Kamu adalah Taspen Sentiment Platform Analysis Agent. "
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
