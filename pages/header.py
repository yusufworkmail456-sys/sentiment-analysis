"""Shared topbar for all pages: dual logo (Taspen + Mitra Digital)."""
import base64
from pathlib import Path

import streamlit as st
import ui


def _b64_img(path: str, mime: str = "image/svg+xml") -> str:
    p = Path(path)
    if not p.exists():
        return ""
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def topbar(page_title: str, page_desc: str) -> None:
    taspen_src  = _b64_img("assets/taspen.svg",  "image/svg+xml")
    mitra_src   = _b64_img("assets/logo2.jpg",   "image/jpeg")

    taspen_img = (
        f'<img src="{taspen_src}" alt="Taspen" '
        f'style="height:28px;object-fit:contain;" />'
        if taspen_src else
        f'<span style="font-weight:900;font-size:.9rem;color:{ui.NAVY};">TASPEN</span>'
    )
    mitra_img = (
        f'<img src="{mitra_src}" alt="Aku Mitra Digital" '
        f'style="height:26px;object-fit:contain;" />'
        if mitra_src else
        f'<span style="font-weight:700;font-size:.8rem;color:{ui.GOLD_DARK};">MITRA DIGITAL</span>'
    )

    st.markdown(f"""
    <div class="tsp-topbar">
      <div class="tsp-topbar-left">
        <div class="tsp-topbar-title">{ui.esc(page_title)}</div>
        <div class="tsp-topbar-desc">{ui.esc(page_desc)}</div>
      </div>
      <div class="tsp-topbar-brand">
        <div class="tsp-topbar-logos">
          {taspen_img}
          <span class="tsp-topbar-divider"></span>
          {mitra_img}
        </div>
        <div class="tsp-topbar-app-name">Taspen Sentiment Platform</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
