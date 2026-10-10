#!/usr/bin/env python3
"""Scraper multi-source: Instagram, YouTube, Web (Google News) -> baris CSV seragam.

Skema baris: source, text, author, date, likes, url
Pakai:
  ./venv/bin/python multiscrape.py --keyword "your-keyword" --ig 50 --yt 50 --web 8 --out multi.csv
"""
import argparse
import csv
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

WARP_PROXY = os.environ.get("IG_PROXY", "socks5://127.0.0.1:40000")
SESSION_FILE = Path(__file__).parent / "ig_session.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _http_get(url, proxy=False, timeout=25, **kw):
    proxies = {"http": WARP_PROXY, "https": WARP_PROXY} if proxy else None
    return requests.get(url, timeout=timeout, headers={"User-Agent": UA},
                        proxies=proxies, **kw)


# ---------------------------------------------------------------- Instagram
def scrape_ig(keyword, max_comments=100, log=print):
    """Komentar IG per hashtag. Pakai web API (session_id dari browser)."""
    try:
        from ig_web_scraper import scrape_ig as _scrape_ig_web
        return _scrape_ig_web(keyword, max_comments, log)
    except RuntimeError:
        raise
    except Exception as e:
        log(f"IG: web scraper gagal ({type(e).__name__}), fallback ke instagrapi...")
        return _scrape_ig_instagrapi(keyword, max_comments, log)


def _scrape_ig_instagrapi(keyword, max_comments=100, log=print):
    """Fallback: instagrapi (butuh ig_session.json atau user/pass)."""
    from instagrapi import Client

    tag = keyword.strip().lstrip("#").replace(" ", "").lower()
    if not tag:
        raise RuntimeError("keyword IG kosong")

    cl = Client()
    cl.delay_range = [2, 5]
    proxy = os.environ.get("IG_PROXY")
    if proxy:
        cl.set_proxy(proxy)
        log("IG: proxy WARP aktif")

    ok = False
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()
            ok = True
            log("IG: login dari sesi tersimpan ok")
        except Exception as e:
            log(f"IG: sesi tersimpan kadaluarsa ({type(e).__name__})")
    if not ok:
        # Fallback: UI credential form (sessions/instagram.json)
        ui_sess = {}
        try:
            from scrapers_extra import _load_session
            s = _load_session("instagram")
            if isinstance(s, dict):
                ui_sess = s
        except Exception:
            pass
        sid = ui_sess.get("session_id") or os.environ.get("IG_SESSIONID")
        # Decode URL-encoded session_id (browser copies %3A instead of :)
        if sid and "%" in sid:
            import urllib.parse
            sid = urllib.parse.unquote(sid)
        user = ui_sess.get("username") or os.environ.get("IG_USER")
        pwd = ui_sess.get("password") or os.environ.get("IG_PASS")
        try:
            if sid:
                cl.login_by_sessionid(sid)
                cl.get_timeline_feed()
                cl.dump_settings(SESSION_FILE)
                ok = True
                log("IG: login via session_id ok")
        except Exception as e:
            log(f"IG: session_id gagal: {type(e).__name__} {str(e)[:100]}")
        if not ok and user and pwd:
            try:
                cl.login(user, pwd)
                cl.get_timeline_feed()
                cl.dump_settings(SESSION_FILE)
                ok = True
                log("IG: login via username/password ok")
            except Exception as e:
                log(f"IG: login user/pass gagal: {type(e).__name__} {str(e)[:100]}")
    if not ok:
        raise RuntimeError("IG login gagal. Coba pakai session_id dari browser: "
                           "login instagram.com → DevTools → Application → Cookies → "
                           "copy nilai sessionid → paste di form IG")

    posts_needed = max(3, min(15, math.ceil(max_comments / 25) + 2))
    log(f"IG: cari postingan #{tag} (target {posts_needed} post) ...")
    medias = []
    for fn in ("hashtag_medias_top_v1", "hashtag_medias_recent_v1"):
        try:
            cand = getattr(cl, fn)(tag, amount=max(posts_needed * 3, 18))
            bercomment = [m for m in cand
                          if (getattr(m, "comment_count", 0) or 0) > 0]
            log(f"IG: {fn}: {len(cand)} post, {len(bercomment)} ber komentar")
            medias = bercomment[:posts_needed]
            if len(medias) >= posts_needed:
                break
        except Exception as e:
            log(f"IG: {fn} gagal: {type(e).__name__} {str(e)[:100]}")
    if not medias:
        return []

    rows = []
    for i, m in enumerate(medias, 1):
        if len(rows) >= max_comments:
            break
        sisa = max_comments - len(rows)
        try:
            comments = cl.media_comments_public_gql(m.code, amount=min(50, sisa))
        except Exception as e:
            log(f"IG: [{i}] {m.code} gagal: {type(e).__name__} {str(e)[:80]}")
            continue
        post_url = f"https://www.instagram.com/p/{m.code}/"
        for c in comments:
            u = c.get("user") or {}
            ts = c.get("created_at_utc")
            rows.append({
                "source": "instagram",
                "text": (c.get("text") or "").replace("\n", " ").strip(),
                "author": u.get("username", ""),
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                        if ts else "",
                "likes": c.get("comment_like_count", 0) or 0,
                "url": post_url,
            })
        log(f"IG: [{i}/{len(medias)}] {m.code}: +{len(comments)} "
            f"(total {len(rows)})")
        time.sleep(2)
    return rows


# ----------------------------------------------------------------- YouTube
def scrape_yt(keyword, max_comments=100, log=print):
    import yt_dlp
    from youtube_comment_downloader import (SORT_BY_POPULAR, SORT_BY_RECENT,
                                            YoutubeCommentDownloader)
    _yt_sort = SORT_BY_RECENT  # newest first for trend tracking

    def search(query, proxy=None):
        opts = {"quiet": True, "extract_flat": True, "skip_download": True,
                "noplaylist": True}
        if proxy:
            opts["proxy"] = proxy
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch8:{query}", download=False)
        return info.get("entries") or []

    entries = []
    try:
        entries = search(keyword)
        log(f"YT: search ok, {len(entries)} video")
    except Exception as e:
        log(f"YT: search direct gagal ({str(e)[:80]}), coba via WARP ...")
        entries = search(keyword, proxy=WARP_PROXY)
        log(f"YT: search via WARP ok, {len(entries)} video")
    if not entries:
        return []

    dl = YoutubeCommentDownloader()
    rows = []
    video_entries = []
    for ent in entries:
        ent_url = ent.get("url", "")
        ent_id = ent.get("id", "")
        # Skip channel results: their URL contains '/channel/' and their ID
        # starts with 'UC' (24 chars).  Only keep actual video entries.
        if "/channel/" in ent_url:
            continue
        if ent_id and len(ent_id) == 24 and ent_id.startswith("UC"):
            continue
        if "watch?v=" not in ent_url and not ent_id:
            continue
        video_entries.append(ent)

    log(f"YT: {len(video_entries)} video (filtered from {len(entries)} entries)")
    for ent in video_entries:
        if len(rows) >= max_comments:
            break
        vid = ent.get("id")
        if not vid:
            continue
        url = f"https://www.youtube.com/watch?v={vid}"
        sisa = max_comments - len(rows)
        got = 0
        try:
            for c in dl.get_comments_from_url(url, sort_by=_yt_sort):
                t = (c.get("text") or "").replace("\n", " ").strip()
                if not t:
                    continue
                tp = c.get("time_parsed")
                if isinstance(tp, (int, float)) and tp:
                    date = datetime.fromtimestamp(tp, tz=timezone.utc).isoformat()
                elif hasattr(tp, "isoformat"):
                    date = tp.isoformat()
                else:
                    date = ""
                rows.append({
                    "source": "youtube",
                    "text": t,
                    "author": c.get("author", "") or "",
                    "date": date,
                    "likes": c.get("votes", 0) or 0,
                    "url": url,
                })
                got += 1
                if got >= sisa:
                    break
        except Exception as e:
            log(f"YT: komentar {vid} gagal: {type(e).__name__} {str(e)[:80]}")
            continue
        judul = (ent.get("title") or "")[:50]
        log(f"YT: {judul}: +{got} (total {len(rows)})")
    return rows


# -------------------------------------------------------------- Web berita
def scrape_web(keyword, max_articles=10, log=print):
    import feedparser
    import trafilatura

    from urllib.parse import parse_qs, quote, unquote, urlparse
    rss = (f"https://www.bing.com/news/search?q={quote(keyword)}"
           f"&format=RSS&setmkt=id-ID&setlang=id")
    try:
        r = _http_get(rss)
        r.raise_for_status()
        log("web: RSS Bing News ok (direct)")
    except Exception as e:
        log(f"web: RSS direct gagal ({str(e)[:60]}), via WARP ...")
        r = _http_get(rss, proxy=True)
        r.raise_for_status()
        log("web: RSS Bing News ok (via WARP)")
    feed = feedparser.parse(r.text)
    log(f"web: {len(feed.entries)} artikel di RSS")

    rows = []
    for ent in feed.entries[: max_articles * 3]:
        if len(rows) >= max_articles:
            break
        link = ent.get("link", "")
        if not link:
            continue
        # link Bing = apiclick.aspx?...&url=<target asli>
        q = parse_qs(urlparse(link).query)
        target = unquote(q.get("url", [link])[0])
        try:
            resp = _http_get(target, allow_redirects=True)
            final_url, html = resp.url, resp.text
        except Exception as e:
            log(f"web: fetch gagal: {str(e)[:60]}")
            continue
        text = trafilatura.extract(html, url=final_url,
                                   include_comments=False) or ""
        text = " ".join(text.split())
        if len(text) < 200:
            continue
        src = ""
        try:
            src = ent.source.title
        except Exception:
            pass
        date = ""
        if ent.get("published_parsed"):
            date = datetime.fromtimestamp(
                time.mktime(ent.published_parsed), tz=timezone.utc).isoformat()
        rows.append({
            "source": "web",
            "text": text[:3000],
            "author": src,
            "date": date,
            "likes": 0,
            "url": final_url,
        })
        log(f"web: {src or final_url[:40]}: ok (total {len(rows)})")
    return rows


# ------------------------------------------------------------------ util
def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        key = (r["source"], r["text"].lower()[:200])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--ig", type=int, default=0, help="max komentar IG")
    ap.add_argument("--yt", type=int, default=0, help="max komentar YouTube")
    ap.add_argument("--web", type=int, default=0, help="max artikel web")
    ap.add_argument("--out", default="multi.csv")
    args = ap.parse_args()

    rows = []
    if args.ig > 0:
        try:
            rows += scrape_ig(args.keyword, args.ig)
        except Exception as e:
            print(f"[!] IG gagal: {e}", file=sys.stderr)
    if args.yt > 0:
        try:
            rows += scrape_yt(args.keyword, args.yt)
        except Exception as e:
            print(f"[!] YT gagal: {e}", file=sys.stderr)
    if args.web > 0:
        try:
            rows += scrape_web(args.keyword, args.web)
        except Exception as e:
            print(f"[!] web gagal: {e}", file=sys.stderr)

    rows = dedupe(rows)
    if not rows:
        print("[!] tidak ada data", file=sys.stderr)
        return 1
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "text", "author", "date",
                                          "likes", "url"])
        w.writeheader()
        w.writerows(rows)
    per = {}
    for r in rows:
        per[r["source"]] = per.get(r["source"], 0) + 1
    print(f"[ok] {len(rows)} baris -> {args.out} | per source: {per}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------- Scrape per URL
def scrape_url_ig(url, max_comments=100, log=print):
    """Scrape comments from a single Instagram post URL."""
    from ig_web_scraper import _load_session_id, _make_session, _get_comments
    import re as _re

    sid, username = _load_session_id()
    if not sid:
        raise RuntimeError("IG butuh login: paste session_id di form Kredensial")

    session = _make_session(sid, username)

    # Extract shortcode from URL
    match = _re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)", url)
    if not match:
        raise RuntimeError(f"URL tidak valid: {url}")
    shortcode = match.group(1)

    # Get media_id from shortcode using GraphQL
    try:
        r = session.get(
            f"https://www.instagram.com/api/v1/media/shortcode/{shortcode}/",
            timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"IG: tidak bisa ambil media_id (HTTP {r.status_code})")
        data = r.json()
        post_id = data.get("pk") or data.get("id", "")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"IG: gagal ambil info post: {e}")

    if not post_id:
        raise RuntimeError("IG: media_id tidak ditemukan")

    return _get_comments(session, str(post_id), shortcode=shortcode,
                         max_comments=max_comments, log=log)


def scrape_url_yt(url, max_comments=100, log=print):
    """Scrape comments from a single YouTube video URL."""
    from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_RECENT
    from datetime import datetime, timezone

    dl = YoutubeCommentDownloader()
    rows = []
    try:
        for c in dl.get_comments_from_url(url, sort_by=SORT_BY_RECENT):
            t = (c.get("text") or "").replace("\n", " ").strip()
            if not t:
                continue
            tp = c.get("time_parsed")
            if isinstance(tp, (int, float)) and tp:
                date = datetime.fromtimestamp(tp, tz=timezone.utc).isoformat()
            elif hasattr(tp, "isoformat"):
                date = tp.isoformat()
            else:
                date = ""
            rows.append({
                "source": "youtube",
                "text": t,
                "author": c.get("author", "") or "",
                "date": date,
                "likes": c.get("votes", 0) or 0,
                "url": url,
            })
            log(f"YT URL: {len(rows)} komentar")
            if len(rows) >= max_comments:
                break
    except Exception as e:
        raise RuntimeError(f"YT: gagal scrape URL: {e}")
    return rows


def scrape_url_facebook(url, max_comments=100, log=print):
    """Scrape a single Facebook post URL via Playwright."""
    from scrapers_extra import _load_session, _parse_cookie_str
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    session = _load_session("facebook")
    if not session:
        raise RuntimeError("Facebook belum dikonfigurasi.")
    cookie_str = session.get("cookie", "")
    if not cookie_str:
        raise RuntimeError("Cookie Facebook kosong.")

    cookies = _parse_cookie_str(cookie_str)
    if "c_user" not in cookies or "xs" not in cookies:
        raise RuntimeError("Cookie tidak lengkap (butuh c_user + xs).")

    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            viewport={"width": 1280, "height": 1024},
        )
        pw_cookies = [
            {"name": k, "value": v, "domain": ".facebook.com", "path": "/"}
            for k, v in cookies.items()
        ]
        context.add_cookies(pw_cookies)
        page = context.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except PWTimeout:
            browser.close()
            raise RuntimeError("Facebook: timeout loading page")

        page.wait_for_timeout(5000)
        # Expand comments
        for _ in range(5):
            btns = page.query_selector_all('[role="button"]:has-text("View more comments")')
            if not btns:
                break
            for b in btns[:3]:
                try:
                    b.click(timeout=3000)
                    page.wait_for_timeout(1200)
                except Exception:
                    pass

        # Extract comments
        comment_els = page.query_selector_all('[aria-label="Comment"]')
        for el in comment_els:
            if len(rows) >= max_comments:
                break
            try:
                text = el.inner_text().strip().replace("\n", " ")
                if len(text) < 5:
                    continue
                rows.append({
                    "source": "facebook",
                    "text": text[:3000],
                    "author": "",
                    "date": "",
                    "likes": 0,
                    "url": url,
                })
            except Exception:
                continue
        browser.close()
    log(f"Facebook URL: {len(rows)} komentar")
    return rows


def scrape_url_tiktok(url, max_comments=100, log=print):
    """Scrape comments from a single TikTok video URL."""
    from scrapers_extra import _load_session
    from datetime import datetime, timezone
    import asyncio

    session = _load_session("tiktok")
    if not session:
        raise RuntimeError("TikTok belum dikonfigurasi.")
    ms_token = session.get("ms_token", "")
    if not ms_token:
        raise RuntimeError("ms_token TikTok kosong.")

    # Extract video ID from URL
    import re as _re
    match = _re.search(r"/video/(\d+)", url)
    if not match:
        raise RuntimeError(f"URL TikTok tidak valid: {url}")
    video_id = match.group(1)

    rows = []
    try:
        from TikTokApi import TikTokApi

        async def _run():
            async with TikTokApi() as api:
                await api.create(ms_token=ms_token, num_retries=2)
                video = api.video(id=video_id)
                async for c in video.comments(count=max_comments):
                    ct = (c.text or "").strip().replace("\n", " ")
                    if len(ct) < 3:
                        continue
                    rows.append({
                        "source": "tiktok",
                        "text": ct[:3000],
                        "author": c.user.nickname or "",
                        "date": "",
                        "likes": c.likes_count or 0,
                        "url": url,
                    })
                    log(f"TikTok URL: {len(rows)} komentar")
                    if len(rows) >= max_comments:
                        break

        asyncio.run(_run())
    except Exception as e:
        raise RuntimeError(f"TikTok: gagal scrape URL: {e}")
    return rows


def scrape_url_web(url, max_comments=1, log=print):
    """Fetch and extract text from a single web/news article URL."""
    import trafilatura
    from datetime import datetime, timezone

    try:
        r = _http_get(url, allow_redirects=True)
        html = r.text
        final_url = r.url
    except Exception as e:
        raise RuntimeError(f"Web: gagal fetch URL: {e}")

    text = trafilatura.extract(html, url=final_url, include_comments=False) or ""
    text = " ".join(text.split())
    if len(text) < 100:
        raise RuntimeError("Web: konten terlalu pendek atau tidak bisa diekstrak.")

    log(f"Web URL: {len(text)} karakter diambil")
    return [{
        "source": "web",
        "text": text[:6000],
        "author": "",
        "date": datetime.now(tz=timezone.utc).isoformat(),
        "likes": 0,
        "url": final_url,
    }]


URL_SCRAPERS = {
    "instagram": scrape_url_ig,
    "youtube": scrape_url_yt,
    "facebook": scrape_url_facebook,
    "tiktok": scrape_url_tiktok,
    "web": scrape_url_web,
}
