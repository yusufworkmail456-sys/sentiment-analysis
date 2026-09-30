#!/usr/bin/env python3
"""Kirim pesan + link file via LINE push message.

Pakai: ./venv/bin/python line_send.py --to <userId> --text "pesan" [--file /path/file.csv]
File di-host di https://grumble-matchbook-dispersed.ngrok-free.dev/files/<nama>?key=<FILE_KEY>
"""
import argparse
import hashlib
import os
import shutil
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv("/root/.hermes/.env")
TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
FILES_DIR = Path("/var/www/ig-files")
FILE_KEY = os.environ.get("IG_FILES_KEY", "")
BASE = "https://grumble-matchbook-dispersed.ngrok-free.dev"


def host_file(path: str) -> str:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(path)
    # nama unik: timestamp + hash pendek
    stamp = time.strftime("%Y%m%d-%H%M%S")
    h = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
    dest = FILES_DIR / f"{src.stem}-{stamp}-{h}{src.suffix}"
    shutil.copy2(src, dest)
    os.chmod(dest, 0o644)
    return f"{BASE}/files/{dest.name}?key={FILE_KEY}"


def push(to: str, text: str) -> None:
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"to": to, "messages": [{"type": "text", "text": text}]},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"[!] LINE push gagal {r.status_code}: {r.text[:200]}", file=sys.stderr)
        sys.exit(1)
    print("[✓] terkirim")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="LINE userId penerima")
    ap.add_argument("--text", required=True)
    ap.add_argument("--file", help="file yang di-host + link disertakan")
    args = ap.parse_args()

    text = args.text
    if args.file:
        url = host_file(args.file)
        text = f"{text}\n\n📎 Raw data (CSV):\n{url}"
    push(args.to, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
