"""Shared topbar for all pages: fixed white bar, brand right."""
import streamlit as st
import ui


def topbar(page_title, page_desc):
    st.markdown(f"""
    <div class="tsp-topbar">
      <div>
        <div class="tsp-topbar-title">{ui.esc(page_title)}</div>
        <div class="tsp-topbar-desc">{ui.esc(page_desc)}</div>
      </div>
      <div class="tsp-topbar-brand">
        <div>
          <div class="tsp-topbar-sub">Taspen Sentiment Platform</div>
          <div class="tsp-topbar-sub2">by Mitra Digital</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
