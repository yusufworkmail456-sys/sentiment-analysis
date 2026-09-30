#!/usr/bin/env python3
"""Scraper tambahan: Facebook, TikTok, Play Store reviews.
Skema baris sama dengan multiscrape.py: source, text, author, date, likes, url.
"""
import os
import time
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from config import PLAYSTORE_APPS

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

WARP_PROXY = os.environ.get("IG_PROXY", "socks5://127.0.0.1:40000")

SESSION_DIR = Path(__file__).parent / "sessions"
SESSION_DIR.mkdir(exist_ok=True)


# =============================================================== FACEBOOK
def scrape_facebook(keyword, max_comments=100, log=print):
    """Facebook search via facebook-scraper. Butuh cookie session."""
    from facebook_scraper import get_posts

    cookie_str = _load_session("facebook")
    if not cookie_str:
        raise RuntimeError("Facebook belum dikonfigurasi. Paste cookie session "
                           "di bagian Kredensial.")

    cookies = _parse_cookie_str(cookie_str)

    rows = []
    log(f"Facebook: cari '{keyword}' ...")

    try:
        posts = get_posts(
            search=keyword,
            pages=max(3, min(10, max_comments // 20)),
            cookies=cookies,
            options={"comments": True, "reactors": True},
            extra_info=True,
        )
    except Exception as e:
        log(f"Facebook: search gagal: {type(e).__name__} {str(e)[:100]}")
        return []

    count = 0
    for post in posts:
        if count >= max_comments:
            break
        ptext = (post.get("post_text") or "").strip().replace("\n", " ")
        if ptext:
            rows.append({
                "source": "facebook",
                "text": ptext[:3000],
                "author": post.get("username", ""),
                "date": str(post.get("time", "")),
                "likes": post.get("likes", 0) or 0,
                "url": post.get("post_url", ""),
            })
            count += 1

        comments = post.get("comments_full") or []
        for c in comments:
            if count >= max_comments:
                break
            ct = (c.get("comment_text") or "").strip().replace("\n", " ")
            if len(ct) < 5:
                continue
            rows.append({
                "source": "facebook",
                "text": ct[:3000],
                "author": c.get("commenter_name", ""),
                "date": str(c.get("comment_time", "")),
                "likes": c.get("comment_reactors", 0) or 0,
                "url": post.get("post_url", ""),
            })
            count += 1

        log(f"Facebook: '{(post.get('post_text') or '')[:40]}': "
            f"total {len(rows)}")

    return rows[:max_comments]


# ================================================================ TIKTOK
def scrape_tiktok(keyword, max_comments=100, log=print):
    """TikTok hashtag search via TikTokApi. Butuh ms_token."""
    from TikTokApi import TikTokApi

    ms_token = _load_session("tiktok")
    if not ms_token:
        raise RuntimeError("TikTok belum dikonfigurasi. Paste ms_token di "
                           "bagian Kredensial.")

    rows = []
    log(f"TikTok: cari '#{keyword}' ...")

    try:
        async def _run():
            async with TikTokApi() as api:
                await api.create(
                    ms_token=ms_token,
                    num_retries=2,
                )
                tag = api.hashtag(name=keyword.replace(" ", ""))
                count = 0
                async for video in tag.videos(count=max(5, max_comments // 20)):
                    if count >= max_comments:
                        break
                    desc = video.info.full_desc or ""
                    if desc:
                        rows.append({
                            "source": "tiktok",
                            "text": desc[:3000],
                            "author": video.info.author.nickname or "",
                            "date": datetime.fromtimestamp(
                                video.info.create_time, tz=timezone.utc
                            ).isoformat() if video.info.create_time else "",
                            "likes": video.info.stats.digg_count or 0,
                            "url": f"https://www.tiktok.com/@{video.info.author.unique_id}/video/{video.info.id}",
                        })
                        count += 1

                    try:
                        async for c in video.comments(count=max_comments - count):
                            if count >= max_comments:
                                break
                            ct = (c.text or "").strip().replace("\n", " ")
                            if len(ct) < 3:
                                continue
                            rows.append({
                                "source": "tiktok",
                                "text": ct[:3000],
                                "author": c.user.nickname or "",
                                "date": "",
                                "likes": c.likes_count or 0,
                                "url": f"https://www.tiktok.com/@{video.info.author.unique_id}/video/{video.info.id}",
                            })
                            count += 1
                    except Exception:
                        pass
                    log(f"TikTok: video {count}: total {len(rows)}")

        import asyncio
        asyncio.run(_run())
    except Exception as e:
        log(f"TikTok: gagal: {type(e).__name__} {str(e)[:100]}")
        return []

    return rows[:max_comments]


# ============================================================ PLAY STORE
# Apps configured in config.py / .env (PLAYSTORE_APPS)


def scrape_playstore(keyword, max_comments=100, log=print):
    """Scrape Google Play Store reviews for configured apps.
    No login needed.
    """
    from google_play_scraper import reviews, search, Sort

    rows = []
    keyword_lower = keyword.strip().lower()
    apps_to_scrape = []

    # Check if keyword matches a known app name
    for app_name, pkg in PLAYSTORE_APPS.items():
        if app_name.lower() in keyword_lower or pkg in keyword_lower:
            apps_to_scrape.append((app_name, pkg))

    # If no direct match, use all known apps
    if not apps_to_scrape:
        if True:  # keyword-based matching removed for generic use
            apps_to_scrape = list(PLAYSTORE_APPS.items())
        else:
            # Search Play Store for the keyword
            try:
                search_results = search(keyword.strip(), n_hits=5, lang="id", country="id")
                for r in search_results:
                    apps_to_scrape.append((r.get("title", r.get("appName", "?")), r["appId"]))
                log(f"Play Store: search '{keyword}' -> {len(apps_to_scrape)} apps")
            except Exception as e:
                log(f"Play Store: search gagal: {str(e)[:80]}")
                apps_to_scrape = list(PLAYSTORE_APPS.items())

    if not apps_to_scrape:
        log("Play Store: tidak ada app ditemukan")
        return []

    per_app = max(10, max_comments // max(len(apps_to_scrape), 1))
    total_collected = 0
    is_known_app = any(keyword_lower in an.lower() or pkg in keyword_lower
                      for an, pkg in PLAYSTORE_APPS.items())

    for app_name, pkg_id in apps_to_scrape:
        if total_collected >= max_comments:
            break
        try:
            result, _ = reviews(
                pkg_id,
                lang="id",
                country="id",
                sort=Sort.NEWEST,
                count=min(per_app, max_comments - total_collected),
            )
            for r in result:
                if total_collected >= max_comments:
                    break
                text = (r.get("content") or "").strip().replace("\n", " ")
                if len(text) < 5:
                    continue
                # If keyword is not a known app, filter reviews by keyword
                if not is_known_app:
                    if keyword_lower not in text.lower():
                        continue
                rows.append({
                    "source": "playstore",
                    "text": text[:3000],
                    "author": r.get("userName", ""),
                    "date": r.get("at").isoformat() if r.get("at") else "",
                    "likes": r.get("thumbsUpCount", 0) or 0,
                    "url": f"https://play.google.com/store/apps/details?id={pkg_id}",
                })
                total_collected += 1
            log(f"Play Store: '{app_name}': +{len(result)} reviews (total {total_collected})")
        except Exception as e:
            log(f"Play Store: '{app_name}' gagal: {type(e).__name__} {str(e)[:80]}")
        time.sleep(0.5)

    return rows[:max_comments]


# ========================================================= SESSION STORE
def _load_session(platform):
    f = SESSION_DIR / f"{platform}.json"
    if f.exists():
        try:
            with open(f) as fh:
                data = json.load(fh)
            return data
        except Exception:
            return None
    return None


def save_session(platform, data):
    f = SESSION_DIR / f"{platform}.json"
    with open(f, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return str(f)


def check_session(platform):
    data = _load_session(platform)
    if not data:
        return "not_setup"
    if platform == "facebook":
        if data.get("cookie"):
            return "ok"
        return "incomplete"
    if platform == "tiktok":
        if data.get("ms_token"):
            return "ok"
        return "incomplete"
    if platform == "instagram":
        if data.get("username") or data.get("session_id"):
            return "ok"
        return "incomplete"
    return "not_setup"


def _parse_cookie_str(cookie_str):
    cookies = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def test_facebook(cookie_str):
    cookies = _parse_cookie_str(cookie_str)
    if "c_user" not in cookies or "xs" not in cookies:
        return False, "Cookie tidak lengkap. Butuh c_user dan xs."
    return True, "Cookie Facebook OK"


def test_tiktok(ms_token):
    if len(ms_token) < 50:
        return False, "ms_token terlalu pendek. Token valid biasanya 100+ chars."
    return True, "ms_token format OK"
