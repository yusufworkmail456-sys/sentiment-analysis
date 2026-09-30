#!/usr/bin/env python3
"""Host dokumentasi (PDF + MD) dan push link-nya ke LINE owner."""
import sys

sys.path.insert(0, "/root/ig-sentiment")
import line_send

TO = "Ub74d3487b50860ee199e86c67b8ee99b"

url_pdf = line_send.host_file("/root/ig-sentiment/docs/DOKUMENTASI.pdf")
url_md = line_send.host_file("/root/ig-sentiment/docs/DOKUMENTASI.md")

text = (
    "📄 Dokumentasi Sistem Sentiment Analysis Multi-Source\n"
    "(Hermes + LINE + Streamlit)\n\n"
    "Isi: ringkasan sistem, diagram arsitektur, komponen & layanan "
    "VPS, perawatan rutin + troubleshooting (404 tunnel, IG expired, "
    "LINE down), cara pakai via Streamlit/LINE/Hermes, model "
    "sentimen, keamanan, batasan, quick reference.\n\n"
    "📕 PDF (5 halaman, ada diagram):\n" + url_pdf + "\n\n"
    "📝 Markdown (sumber):\n" + url_md + "\n\n"
    "Link berlaku selama tunnel ngrok aktif."
)

line_send.push(TO, text)
print("PDF:", url_pdf[:60] + "...")
print("MD :", url_md[:60] + "...")
