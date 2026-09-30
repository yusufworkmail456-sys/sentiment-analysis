#!/usr/bin/env python3
"""Scrape komentar Instagram berdasarkan KEYWORD/HASHTAG -> CSV.

Pakai:
  IG_SESSIONID=xxx ./venv/bin/python keyword_scrape.py --keyword "kuliner" \
      --posts 5 --per-post 30 --out komentar.csv

Login WAJIB (pencarian hashtag IG tidak ada jalur anonim):
  - IG_SESSIONID  : cookie sessionid dari browser (cepat)
  - IG_USER+IG_PASS : username + password (fallback)

Kredensial dibaca dari env, TIDAK disimpan ke file.
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
    cl.delay_range = [2, 5]
    proxy = os.environ.get("IG_PROXY")
    if proxy:
        cl.set_proxy(proxy)
        print("[i] proxy aktif", file=sys.stderr)
    return cl


def try_login(cl: Client) -> bool:
    sessionid = os.environ.get("IG_SESSIONID")
    user = os.environ.get("IG_USER")
    pwd = os.environ.get("IG_PASS")
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            print("[i] login ok dari sesi tersimpan", file=sys.stderr)
            return True
        except Exception:
            pass
    if sessionid:
        try:
            cl.login_by_sessionid(sessionid)
            cl.get_timeline_feed()
            cl.dump_settings(SESSION_FILE)
            print("[i] login ok via sessionid", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[!] login sessionid gagal: {e}", file=sys.stderr)
    if user and pwd:
        try:
            cl.login(user, pwd)
            cl.get_timeline_feed()
            cl.dump_settings(SESSION_FILE)
            print(f"[i] login ok sebagai {user}", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[!] login gagal: {e}", file=sys.stderr)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True,
                    help="hashtag/keyword, contoh: kuliner atau #kuliner")
    ap.add_argument("--posts", type=int, default=5,
                    help="jumlah postingan per keyword (default 5)")
    ap.add_argument("--per-post", type=int, default=30,
                    help="jumlah komentar per postingan (default 30)")
    ap.add_argument("--out", default="komentar.csv", help="file CSV output")
    args = ap.parse_args()

    tag = args.keyword.strip().lstrip("#").replace(" ", "")
    if not tag:
        print("[!] keyword kosong", file=sys.stderr)
        return 1

    cl = make_client()
    if not try_login(cl):
        print("[!] GAGAL: pencarian hashtag butuh login. Set IG_SESSIONID "
              "atau IG_USER+IG_PASS di env.", file=sys.stderr)
        return 2

    # 1. ambil postingan dari hashtag (TOP dulu = sudah ada engagement,
    #    RECENT sebagai fallback), buang yang 0 komentar
    print(f"[i] cari postingan #{tag} (target {args.posts}) ...", file=sys.stderr)
    medias = []
    for fn in ("hashtag_medias_top_v1", "hashtag_medias_recent_v1"):
        try:
            cand = getattr(cl, fn)(tag, amount=max(args.posts * 3, 18))
            bercomment = [m for m in cand
                          if (getattr(m, "comment_count", 0) or 0) > 0]
            print(f"[i] {fn}: {len(cand)} postingan, {len(bercomment)} "
                  f"punya komentar", file=sys.stderr)
            medias = bercomment[:args.posts]
            if len(medias) >= args.posts:
                break
        except Exception as e:
            print(f"[!] {fn} gagal: {type(e).__name__} {str(e)[:120]}",
                  file=sys.stderr)
    if not medias:
        print("[!] tidak ada postingan ditemukan", file=sys.stderr)
        return 3

    # 2. ambil komentar tiap postingan
    rows = []
    for i, m in enumerate(medias, 1):
        cc = getattr(m, "comment_count", 0) or 0
        if cc == 0:
            print(f"  [{i}/{len(medias)}] {m.code}: 0 komentar, skip",
                  file=sys.stderr)
            continue
        try:
            comments = cl.media_comments_public_gql(m.code,
                                                    amount=args.per_post)
        except Exception:
            try:
                comments = cl.media_comments_gql(str(m.pk),
                                                 amount=args.per_post)
            except Exception as e:
                print(f"  [{i}/{len(medias)}] {m.code}: gagal ambil komentar "
                      f"{type(e).__name__} {str(e)[:100]}", file=sys.stderr)
                continue
        post_url = f"https://www.instagram.com/p/{m.code}/"
        for c in comments:
            u = c.get("user") or {}
            rows.append({
                "post_code": m.code,
                "post_url": post_url,
                "pk": c.get("pk", ""),
                "username": u.get("username", ""),
                "text": (c.get("text") or "").replace("\n", " ").strip(),
                "likes": c.get("comment_like_count", 0) or 0,
                "created_at": c.get("created_at_utc", ""),
            })
        print(f"  [{i}/{len(medias)}] {m.code}: {len(comments)} komentar "
              f"(total {len(rows)})", file=sys.stderr)
        time.sleep(2)

    if not rows:
        print("[!] tidak ada komentar terkumpul", file=sys.stderr)
        return 4

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[✓] {len(rows)} komentar dari {len(medias)} postingan -> {args.out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
