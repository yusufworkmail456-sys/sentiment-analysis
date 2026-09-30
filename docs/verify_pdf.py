#!/usr/bin/env python3
"""Verifikasi isi PDF: jumlah halaman + potongan teks per halaman."""
import json
import subprocess
import sys

PDF = "/root/ig-sentiment/docs/DOKUMENTASI.pdf"
SCRIPT = "/root/.hermes/skills/productivity/pdf/scripts/pdf_read.py"
PY = "/root/ig-sentiment/venv/bin/python"

r = subprocess.run([PY, SCRIPT, PDF, "--text"], capture_output=True, text=True)
data = json.loads(r.stdout)
pages = data if isinstance(data, list) else data.get("pages", [])
print("type:", type(data).__name__, "| count:", len(pages))
for i, p in enumerate(pages, 1):
    if isinstance(p, str):
        text = p
    else:
        text = p.get("text") or ""
    text = text.strip()
    flat = " | ".join(text.split("\n"))
    print(f"--- hal {i} ({len(text)} chars): {flat[:200]}")
