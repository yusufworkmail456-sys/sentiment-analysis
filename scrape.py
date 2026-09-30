#!/usr/bin/env python3
"""Scrape komentar Instagram dari URL postingan -> CSV.

Pakai:
  ./venv/bin/python scrape.py --url "https://www.instagram.com/p/XXXX/" --out komentar.csv
Login opsional (env IG_USER + IG_PASS) — tanpa login coba jalur publik dulu.
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

from instagrapi import Client

SESSION_FILE = Path(__file__).parent / "ig_session.json"


def make_client() -> Client:
    cl = Client()
    cl.delay_range = [1, 3]
    proxy = os.environ.get("IG_PROXY")
    if proxy:
        cl.set_proxy(proxy)
        print(f"[i] proxy aktif", file=sys.stderr)
    return cl


def try_login(cl: Client) -> bool:
    sessionid = os.environ.get("IG_SESSIONID")
    user = os.environ.get("IG_USER")
    pwd = os.environ.get("IG_PASS")
    if SESSION_FILE.exists():
        cl.load_settings(SESSION_FILE)
    if sessionid:
        try:
            cl.login_by_sessionid(sessionid)
            cl.get_timeline_feed()  # validasi sesi
            cl.dump_settings(SESSION_FILE)
            print("[i] login ok via sessionid", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[!] login sessionid gagal: {e}", file=sys.stderr)
    if not user or not pwd:
        return False
    try:
        cl.login(user, pwd)
        cl.get_timeline_feed()  # validasi sesi
        cl.dump_settings(SESSION_FILE)
        print(f"[i] login ok sebagai {user}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[!] login gagal: {e}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="URL postingan Instagram")
    ap.add_argument("--out", default="komentar.csv", help="file CSV output")
    ap.add_argument("--limit", type=int, default=0, help="batas jumlah komentar (0=all)")
    args = ap.parse_args()

    cl = make_client()
    logged = try_login(cl)

    print("[i] ambil media_id dari URL ...", file=sys.stderr)
    media_pk = cl.media_pk_from_url(args.url)
    print(f"[i] media_pk = {media_pk}", file=sys.stderr)

    rows = []
    if logged:
        print("[i] ambil komentar via API privat (login) ...", file=sys.stderr)
        comments = cl.media_comments(media_pk, amount=args.limit)
        for c in comments:
            rows.append({
                "pk": c.pk,
                "username": c.user.username,
                "text": c.text,
                "likes": c.like_count,
                "created_at": c.created_at_utc.isoformat() if c.created_at_utc else "",
                "replied_to": c.parent_comment_id or "",
            })
    else:
        print("[i] tanpa login: ambil via GraphQL publik ...", file=sys.stderr)
        shortcode = args.url.rstrip("/").split("/p/")[-1].split("/")[0]
        gql = cl.media_comments_public_gql(shortcode, amount=args.limit or 0)
        for c in gql:
            u = c.get("user") or {}
            rows.append({
                "pk": c.get("pk"),
                "username": u.get("username", ""),
                "text": c.get("text", ""),
                "likes": c.get("comment_like_count", 0),
                "created_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%S", time.gmtime(int(c.get("created_at", 0)))
                ),
                "replied_to": c.get("parent_comment_id", "") or "",
            })

    rows = [r for r in rows if r["text"]]
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pk", "username", "text", "likes", "created_at", "replied_to"])
        w.writeheader()
        w.writerows(rows)
    print(f"[✓] {len(rows)} komentar tersimpan -> {args.out}", file=sys.stderr)
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
