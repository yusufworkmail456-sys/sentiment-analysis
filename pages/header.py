"""Shared topbar for all pages (Taspen brand, no Streamlit default header)."""
import streamlit as st
from icons import icon

def topbar(page_title, page_desc):
    st.markdown(f"""
    <div class="tsp-topbar">
      <div>
        <div class="tsp-topbar-title">{page_title}</div>
        <div class="tsp-topbar-desc">{page_desc}</div>
      </div>
      <div class="tsp-topbar-brand">
        <div class="tsp-topbar-sub">Taspen Sentiment Platform</div>
        <div class="tsp-topbar-sub2">by Mitra Digital</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
