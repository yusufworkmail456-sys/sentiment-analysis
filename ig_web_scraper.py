#!/usr/bin/env python3
"""Instagram scraper via web API — no instagrapi needed.
Uses session_id from browser cookies + www.instagram.com/api/v1/ endpoints.
"""
import re
import math
import os
import time
import json
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

WARP_PROXY = os.environ.get("IG_PROXY", "socks5://127.0.0.1:40000")
SESSION_DIR = Path(__file__).parent / "sessions"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _load_session_id():
    """Load session_id from sessions/instagram.json or env."""
    # Try UI form
    f = SESSION_DIR / "instagram.json"
    if f.exists():
        try:
            with open(f) as fh:
                data = json.load(fh)
            sid = data.get("session_id", "")
            if sid:
                if "%" in sid:
                    sid = urllib.parse.unquote(sid)
                return sid, data.get("username", "")
        except Exception:
            pass
    # Try env
    sid = os.environ.get("IG_SESSIONID", "")
    if sid and "%" in sid:
        sid = urllib.parse.unquote(sid)
    return sid or "", ""


def _make_session(sid, username=""):
    """Create requests session with IG cookies + headers."""
    s = requests.Session()
    s.cookies.set("sessionid", sid, domain=".instagram.com")
    user_id = sid.split(":")[0] if ":" in sid else ""
    if user_id:
        s.cookies.set("ds_user_id", user_id, domain=".instagram.com")
    s.headers.update({
        "User-Agent": UA,
        "X-IG-App-ID": "936619743392459",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "X-ASBD-ID": "198387",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.instagram.com/",
    })
    if os.environ.get("IG_PROXY"):
        proxies = {"http": WARP_PROXY, "https": WARP_PROXY}
        s.proxies.update(proxies)
    return s


def _get_timeline_posts(session, max_posts=15, log=print):
    """Get posts from timeline feed — search for keyword in caption."""
    posts = []
    next_max_id = None
    pages = 0
    while len(posts) < max_posts and pages < 3:
        params = {}
        if next_max_id:
            params["max_id"] = next_max_id
        try:
            r = session.get("https://www.instagram.com/api/v1/feed/timeline/",
                            params=params, timeout=15)
            if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                log(f"IG: timeline feed HTTP {r.status_code}")
                break
            data = r.json()
        except Exception as e:
            log(f"IG: timeline feed gagal: {type(e).__name__} {str(e)[:80]}")
            break

        items = data.get("feed_items", [])
        for item in items:
            media = item.get("media_or_ad", {})
            if not media:
                continue
            mid = media.get("id", "")
            cc = media.get("comment_count", 0)
            lc = media.get("like_count", 0)
            cap = media.get("caption", "")
            if isinstance(cap, dict):
                cap = cap.get("text", "")
            if mid and cc > 0:
                code = media.get("code", "")
                posts.append({"id": mid, "shortcode": code, "caption": cap or "", "comments": cc, "likes": lc})
            if len(posts) >= max_posts:
                break

        next_max_id = data.get("next_max_id")
        pages += 1
        if not next_max_id:
            break
        time.sleep(1)

    return posts[:max_posts]


def _get_tag_posts(session, tag, max_posts=15, log=print):
    """Get posts from hashtag via tag sections."""
    posts = []
    next_max_id = ""
    pages = 0
    while len(posts) < max_posts and pages < 3:
        params = {"include_persistent": "0", "max_id": next_max_id} if next_max_id else {"include_persistent": "0"}
        try:
            r = session.get(f"https://www.instagram.com/api/v1/tags/{tag}/sections/",
                            params=params, timeout=15)
            if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                break
            data = r.json()
        except Exception:
            break

        sections = data.get("sections", [])
        for sec in sections:
            medias = sec.get("layout_content", {}).get("medias", [])
            for m in medias:
                media = m.get("media", {})
                mid = media.get("id", "")
                cc = media.get("comment_count", 0)
                lc = media.get("like_count", 0)
                cap = media.get("caption", "")
                if isinstance(cap, dict):
                    cap = cap.get("text", "")
                if mid and cc > 0:
                    code = media.get("code", "")
                    posts.append({"id": mid, "shortcode": code, "caption": cap or "", "comments": cc, "likes": lc})
                if len(posts) >= max_posts:
                    break
            if len(posts) >= max_posts:
                break

        next_max_id = data.get("next_max_id", "")
        more_available = data.get("more_available", False)
        pages += 1
        if not more_available or not next_max_id:
            break
        time.sleep(1)

    return posts[:max_posts]


def _get_comments(session, post_id, shortcode="", max_comments=25, log=print):
    """Fetch comments for a post via web API."""
    # Set Referer to the post page — required for comments endpoint to return JSON
    if shortcode:
        session.headers["Referer"] = f"https://www.instagram.com/p/{shortcode}/"
    comments = []
    next_min_id = None
    pages = 0
    while len(comments) < max_comments and pages < 3:
        params = {"can_support_threading": "true", "permalink_enabled": "false"}
        if next_min_id:
            params["min_id"] = next_min_id
        try:
            r = session.get(
                f"https://www.instagram.com/api/v1/media/{post_id}/comments/",
                params=params, timeout=15)
            if r.status_code != 200:
                break
            ct = r.headers.get("content-type", "")
            if "json" not in ct:
                break
            data = r.json()
        except Exception:
            break

        raw_comments = data.get("comments", [])
        for c in raw_comments:
            text = (c.get("text") or "").strip().replace("\n", " ")
            if not text:
                continue
            username = c.get("user", {}).get("username", "")
            likes = c.get("comment_like_count", 0) or 0
            created = c.get("created_at", 0)
            date = ""
            if created:
                try:
                    date = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                except Exception:
                    date = ""
            comments.append({
                "source": "instagram",
                "text": text[:3000],
                "author": username,
                "date": date,
                "likes": likes,
                "url": f"https://www.instagram.com/p/{post_id}/",
            })
            if len(comments) >= max_comments:
                break

        next_min_id = data.get("next_min_id")
        pages += 1
        if not next_min_id:
            break
        time.sleep(0.5)

    return comments[:max_comments]


def scrape_ig(keyword, max_comments=100, log=print):
    """Scrape Instagram comments via web API.
    Uses session_id from browser cookies (sessions/instagram.json or IG_SESSIONID env).
    """
    sid, username = _load_session_id()
    if not sid:
        raise RuntimeError("IG butuh login: paste session_id di form Kredensial")

    if os.environ.get("IG_PROXY"):
        log("IG: proxy WARP aktif")

    session = _make_session(sid, username)

    tag = keyword.strip().lstrip("#").replace(" ", "").lower()
    if not tag:
        raise RuntimeError("keyword IG kosong")

    # Test session validity — use tag info (lighter than timeline)
    try:
        r = session.get(f"https://www.instagram.com/api/v1/tags/{tag}/info/", timeout=15)
        if r.status_code == 429:
            raise RuntimeError("IG: rate-limited (429). Tunggu 1-2 menit lalu coba lagi.")
        if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            raise RuntimeError(f"IG: session_id invalid/expired (HTTP {r.status_code}). "
                               "Ambil session_id baru dari browser.")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"IG: gagal koneksi: {type(e).__name__} {str(e)[:100]}")

    log("IG: login via session_id ok")

    # Strategy: try hashtag posts first, fallback to timeline
    posts = []
    try:
        log(f"IG: cari postingan #{tag} ...")
        posts = _get_tag_posts(session, tag, max_posts=math.ceil(max_comments / 10) + 3, log=log)
        log(f"IG: hashtag #{tag}: {len(posts)} post dengan komentar")
    except Exception as e:
        log(f"IG: hashtag gagal: {type(e).__name__} {str(e)[:80]}")

    if not posts:
        log("IG: fallback ke timeline feed...")
        posts = _get_timeline_posts(session, max_posts=math.ceil(max_comments / 10) + 3, log=log)
        log(f"IG: timeline: {len(posts)} post dengan komentar")

    if not posts:
        log("IG: tidak ada post dengan komentar")
        return []

    # Fetch comments from posts
    rows = []
    per_post = max(5, max_comments // max(len(posts), 1))
    for post in posts:
        if len(rows) >= max_comments:
            break
        remaining = max_comments - len(rows)
        got = min(per_post, remaining)
        try:
            comments = _get_comments(session, post["id"], shortcode=post.get("shortcode", ""), max_comments=got, log=log)
            rows.extend(comments)
            log(f"IG: post {post['id'][:20]}...: +{len(comments)} komentar (total {len(rows)})")
        except Exception as e:
            log(f"IG: komentar gagal untuk {post['id'][:20]}...: {type(e).__name__} {str(e)[:80]}")
        time.sleep(0.5)

    return rows[:max_comments]
