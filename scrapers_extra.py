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
    """Facebook hashtag search via Playwright. Butuh cookie session (c_user + xs).

    Menggunakan Playwright (headless Chromium) karena facebook_scraper tidak
    bisa parse halaman FB modern (Comet UI / React-rendered).

    User tetap paste cookie di kolom yang sama. Scraper inject cookie ke
    browser, buka halaman hashtag, scroll, dan extract post text.
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    session = _load_session("facebook")
    if not session:
        raise RuntimeError("Facebook belum dikonfigurasi. Paste cookie session "
                           "di bagian Kredensial.")

    cookie_str = session.get("cookie", "") if isinstance(session, dict) else session
    if not cookie_str:
        raise RuntimeError("Cookie Facebook kosong. Paste cookie session "
                           "di bagian Kredensial.")

    cookies = _parse_cookie_str(cookie_str)

    # Validasi: butuh c_user + xs minimum
    if "c_user" not in cookies or "xs" not in cookies:
        raise RuntimeError("Cookie tidak lengkap. Butuh c_user dan xs.")

    rows = []
    log(f"Facebook: cari '#{keyword}' via Playwright ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36",
            viewport={"width": 1280, "height": 1024},
        )

        # Inject cookies
        pw_cookies = [
            {"name": k, "value": v, "domain": ".facebook.com", "path": "/"}
            for k, v in cookies.items()
        ]
        context.add_cookies(pw_cookies)
        page = context.new_page()

        try:
            page.goto(
                f"https://www.facebook.com/hashtag/{keyword}",
                timeout=30000,
                wait_until="domcontentloaded",
            )
        except PWTimeout:
            log("Facebook: timeout loading page")
            browser.close()
            return []

        page.wait_for_timeout(5000)

        # Scroll to load more posts
        scroll_count = min(8, max(2, max_comments // 15))
        for _ in range(scroll_count):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

        # Expand "See more" buttons
        see_mores = page.query_selector_all('div[role="button"]:has-text("See more")')
        for btn in see_mores[:10]:
            try:
                btn.click(timeout=3000)
                page.wait_for_timeout(600)
            except Exception:
                pass

        # Extract posts from feed
        feed = page.query_selector('[role="feed"]')
        if not feed:
            log("Facebook: feed tidak ditemukan (cookie expired?)")
            browser.close()
            return []

        children = feed.query_selector_all(":scope > *")
        for child in children:
            if len(rows) >= max_comments:
                break
            try:
                text = child.inner_text()
            except Exception:
                continue

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            content = [
                l for l in lines
                if l != "Facebook"
                and not l.startswith("Number of")
                and l not in ("·", "Follow", "Active", "Online status indicator")
            ]

            if len(content) < 4:
                continue

            # Author = first line
            author = content[0]

            # Post text: lines after author block, before metadata markers
            post_start = 0
            for j, line in enumerate(content[:6]):
                if line in ("Follow", "·"):
                    post_start = j + 1
                    break

            post_end = len(content)
            markers = (
                "Shared post", "See translation", "See less",
                "May be an image", "No photo", "Send message",
                "View post", "Write a comment", "AI content",
            )
            for j in range(post_start, len(content)):
                if any(content[j].startswith(m) or content[j] == m for m in markers):
                    post_end = j
                    break

            post_text = " ".join(content[post_start:post_end]).strip()
            # Clean up noise
            post_text = post_text.replace("… See more", "").replace("…See more", "")
            post_text = post_text.replace("See less", "").strip()
            # Remove author name prefix from post text (FB sometimes includes it)
            if author and post_text.startswith(author):
                post_text = post_text[len(author):].strip()
            if len(post_text) < 10:
                continue

            # Extract URL
            url = ""
            try:
                link_el = child.query_selector("a[href]")
                if link_el:
                    url = link_el.get_attribute("href") or ""
            except Exception:
                pass

            # Extract likes (first number near end)
            likes = 0
            for j in range(len(content) - 1, post_end - 1, -1):
                try:
                    n = int(content[j].replace(",", ""))
                    if 0 < n < 100000:
                        likes = n
                        break
                except ValueError:
                    continue

            rows.append({
                "source": "facebook",
                "text": post_text[:3000],
                "author": author[:200],
                "date": "",
                "likes": likes,
                "url": url,
            })

            if len(rows) % 5 == 0:
                log(f"Facebook: {len(rows)} baris terkumpul ...")

        browser.close()

    log(f"Facebook: selesai, {len(rows)} baris")
    return rows[:max_comments]


# ================================================================ TIKTOK
def scrape_tiktok(keyword, max_comments=100, log=print):
    """TikTok hashtag search via TikTokApi. Butuh ms_token."""
    from TikTokApi import TikTokApi

    session = _load_session("tiktok")
    if not session:
        raise RuntimeError("TikTok belum dikonfigurasi. Paste ms_token di "
                           "bagian Kredensial.")

    # _load_session returns dict {"ms_token": "..."} — extract the string
    ms_token = session.get("ms_token", "") if isinstance(session, dict) else session
    if not ms_token:
        raise RuntimeError("ms_token TikTok kosong. Paste ms_token di "
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
        if PLAYSTORE_APPS:  # apps configured -> use them
            apps_to_scrape = list(PLAYSTORE_APPS.items())
        else:
            # No apps configured -> search Play Store for the keyword
            try:
                search_results = search(keyword.strip(), n_hits=5, lang="id", country="id")
                for r in search_results:
                    app_id = r.get("appId")
                    if app_id:
                        apps_to_scrape.append((r.get("title", r.get("appName", "?")), app_id))
                log(f"Play Store: search '{keyword}' -> {len(apps_to_scrape)} apps")
            except Exception as e:
                log(f"Play Store: search gagal: {str(e)[:80]}")

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
