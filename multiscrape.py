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
import re
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
def _yt_search_entries(keyword, want, log):
    """Cari video YT dengan retry: direct → WARP proxy → yt-dlp flat ulang.
    Return list entri video (channel results dibuang)."""
    import yt_dlp

    def search(query, proxy=None):
        opts = {"quiet": True, "extract_flat": True, "skip_download": True,
                "noplaylist": True}
        if proxy:
            opts["proxy"] = proxy
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max(8, want)}:{query}", download=False)
        return info.get("entries") or []

    entries = []
    last_err = None
    for attempt, proxy in enumerate([None, WARP_PROXY, None], 1):
        try:
            entries = search(keyword, proxy=proxy)
            log(f"YT: search ok (percobaan {attempt}), {len(entries)} entri")
            break
        except Exception as e:
            last_err = e
            log(f"YT: search percobaan {attempt} gagal ({str(e)[:80]})")
    if not entries and last_err:
        log(f"YT: search gagal total: {type(last_err).__name__} {str(last_err)[:120]}")
    video_entries = []
    for ent in entries:
        ent_url = ent.get("url", "")
        ent_id = ent.get("id", "")
        # Skip channel results: URL '/channel/' atau id UC+24 chars
        if "/channel/" in ent_url:
            continue
        if ent_id and len(ent_id) == 24 and ent_id.startswith("UC"):
            continue
        if "watch?v=" not in ent_url and not ent_id:
            continue
        video_entries.append(ent)
    return video_entries


def _yt_comments_via_downloader(url, sisa, collect):
    """Engine 1: youtube-comment-downloader. Return jumlah komentar terkumpul."""
    from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_RECENT
    dl = YoutubeCommentDownloader()
    got = 0
    for c in dl.get_comments_from_url(url, sort_by=SORT_BY_RECENT):
        if got >= sisa:
            break
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
        collect({
            "source": "youtube",
            "text": t,
            "author": c.get("author", "") or "",
            "date": date,
            "likes": c.get("votes", 0) or 0,
            "url": url,
        })
        got += 1
    return got


def scrape_yt(keyword, max_comments=100, log=print):
    """Komentar YT per keyword. Robust: search retry + 2 engine komentar
    (youtube-comment-downloader → yt-dlp) + chase target dengan video tambahan."""
    rows = []

    def collect(r):
        rows.append(r)

    entries = _yt_search_entries(keyword, max_comments, log)
    if not entries:
        log("YT: tidak ada video ditemukan")
        return []

    log(f"YT: {len(entries)} video (filtered dari hasil search)")
    for ent in entries:
        if len(rows) >= max_comments:
            break
        vid = ent.get("id")
        if not vid:
            continue
        url = f"https://www.youtube.com/watch?v={vid}"
        sisa = max_comments - len(rows)
        got = 0
        try:
            got = _yt_comments_via_downloader(url, sisa, collect)
        except Exception as e:
            log(f"YT: downloader gagal {vid} ({type(e).__name__} {str(e)[:60]}), coba yt-dlp ...")
        # Engine 2: yt-dlp comments jika engine 1 tidak menghasilkan apa pun
        if got == 0:
            got = _yt_comments_via_ytdlp(url, sisa, collect, log)
        judul = (ent.get("title") or "")[:50]
        if got:
            log(f"YT: {judul}: +{got} (total {len(rows)})")
        else:
            log(f"YT: {judul}: 0 komentar (dinonaktifkan atau diblokir)")
    if rows and len(rows) < max_comments:
        log(f"YT: target {max_comments}, didapat {len(rows)} (stok komentar video habis)")
    return rows


def _yt_comments_via_ytdlp(url, sisa, collect, log=print):
    """Engine 2: ambil komentar via yt-dlp (fallback downloader).
    Return jumlah komentar terkumpul."""
    try:
        import yt_dlp

        opts = {"quiet": True, "skip_download": True, "extractor_retries": 1,
                "socket_timeout": 20}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        got = 0
        for c in (info.get("comments") or []):
            if got >= sisa:
                break
            t = (c.get("text") or "").replace("\n", " ").strip()
            if len(t) < 2:
                continue
            date = ""
            ts = c.get("timestamp")
            if ts:
                try:
                    date = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                except Exception:
                    date = ""
            collect({
                "source": "youtube",
                "text": t,
                "author": c.get("author", "") or "",
                "date": date,
                "likes": c.get("like_count", 0) or 0,
                "url": url,
            })
            got += 1
        return got
    except Exception as e:
        log(f"YT: yt-dlp fallback gagal ({type(e).__name__} {str(e)[:80]})")
        return 0


# -------------------------------------------------------------- Web berita
def scrape_web(keyword, max_articles=10, log=print):
    import feedparser
    import trafilatura

    from urllib.parse import parse_qs, quote, unquote, urlparse
    k = quote(keyword)
    feeds = [
        ("Bing News",
         f"https://www.bing.com/news/search?q={k}&format=RSS&setmkt=id-ID&setlang=id"),
        ("Bing Web",
         f"https://www.bing.com/search?q={k}&format=RSS&setmkt=id-ID&setlang=id&count=30"),
    ]

    rows = []
    seen_urls = set()
    for nama_feed, rss in feeds:
        if len(rows) >= max_articles:
            break
        # Bing News RSS bisa dipaginasi via &first=N (1, 11, 21, ...) —
        # 1 halaman cuma ~9-10 entri, sering kurang utk target 10.
        feed_urls = [rss]
        if nama_feed == "Bing News":
            for offset in (11, 21):
                feed_urls.append(f"{rss}&first={offset}")
        entries = []
        seen_links = set()
        for fu in feed_urls:
            try:
                r = _http_get(fu)
                r.raise_for_status()
            except Exception as e:
                log(f"web: {nama_feed} gagal ({str(e)[:60]})")
                continue
            f = feedparser.parse(r.text)
            new = 0
            for ent in f.entries:
                if ent.get("link") and ent["link"] not in seen_links:
                    seen_links.add(ent["link"])
                    entries.append(ent)
                    new += 1
            label_hal = fu.split("first=")[-1] if "first=" in fu else "1"
            log(f"web: {nama_feed} hal {label_hal}: +{new} entri")
            if new == 0:
                break
        log(f"web: {nama_feed}: {len(entries)} entri total")

        for ent in entries:
            if len(rows) >= max_articles:
                break
            link = ent.get("link", "")
            if not link:
                continue
            # link Bing/Google News = redirect -> ambil URL target asli
            q = parse_qs(urlparse(link).query)
            target = unquote(q.get("url", [link])[0])
            if target in seen_urls:
                continue
            host = urlparse(target).netloc.lower()
            if not host or "." not in host:
                continue
            base_host = host[4:] if host.startswith("www.") else host
            if any(base_host == d or base_host.endswith("." + d) or base_host.startswith(d)
                   for d in ("google.com", "youtube.com", "bing.com", "microsoft.com",
                             "facebook.com", "instagram.com", "twitter.com", "x.com",
                             "tiktok.com", "wikipedia.org", "yahoo.com")):
                log(f"web: skip {host} (bukan artikel)")
                continue
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
            seen_urls.add(target)
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


# ------------------------------------------------------------------ fetch_until_target
# Round-robin over-fetch + dedupe antar-round: scraper dipanggil berulang
# dgn permintaan makin besar, hasil digabung lalu didedupe per-sumber, sampai
# jumlah unik per sumber >= target ATAU stok platform beneran habis
# (tidak ada baris unik baru di round terakhir).
MAX_ROUNDS = 4          # max percobaan per sumber
OVERFETCH_FACTOR = 1.6  # buffer permintaan per round (menutup duplikat + filter)


def fetch_until_target(source_name, scraper_fn, keyword, target, log=print):
    """Kembalikan list baris unik dengan panjang mendekati `target`.

    Round 1: panggil scraper dgn `target` (perilaku lama).
    Round 2+: kalau kurang, panggil ulang dgn over-fetch (target*factor) —
    platform biasanya mengembalikan halaman/populasi komentar yang sama,
    tapi kombinasi engine + sort + offset sering menghasilkan tambahan.
    Berhenti saat target tercapai, MAX_ROUNDS habis, atau round tanpa
    baris unik baru (stok habis — jangan buang waktu & jangan kena rate-limit).
    """
    if target <= 0:
        return []
    src_key = source_name.strip().lower()
    pooled: list = []
    seen: set = set()

    def key_of(r):
        return (str(r.get("source", src_key)).lower(), str(r.get("text", "")).lower()[:200])

    def pool_unique(new_rows):
        added = 0
        for r in new_rows or []:
            k = key_of(r)
            if k in seen:
                continue
            seen.add(k)
            pooled.append(r)
            added += 1
        return added

    ask = max(target, 1)
    for rnd in range(1, MAX_ROUNDS + 1):
        try:
            got = scraper_fn(keyword, ask, log)
        except Exception as e:
            log(f"{source_name}: round {rnd} gagal: {type(e).__name__} {str(e)[:120]}")
            got = []
        added = pool_unique(got)
        log(f"{source_name}: round {rnd} +{added} unik (total {len(pooled)}/{target})")
        if len(pooled) >= target:
            break
        if added == 0:
            log(f"{source_name}: stok habis — {len(pooled)}/{target} unik terkumpul")
            break
        ask = math.ceil(len(pooled) * OVERFETCH_FACTOR) + 4

    return pooled[:target]


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

    # Extract shortcode from URL (/p/ or /reel/)
    match = _re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)", url)
    if not match:
        raise RuntimeError(f"URL tidak valid: {url}")
    shortcode = match.group(1)

    # Get media_id from shortcode using web API
    try:
        r = session.get(
            f"https://www.instagram.com/api/v1/media/shortcode/{shortcode}/",
            timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"IG: tidak bisa ambil media_id (HTTP {r.status_code})")
        data = r.json()
        item = data.get("items", [{}])[0] if isinstance(data.get("items"), list) else {}
        post_id = item.get("pk") or data.get("pk") or ""
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"IG: gagal ambil info post: {e}")

    # Correct post URL (from shortcode, not post_id)
    rows = []
    if not post_id:
        raise RuntimeError("IG: media_id tidak ditemukan")

    comments = _get_comments(session, str(post_id), shortcode=shortcode,
                             max_comments=max_comments, log=log)
    for c in comments:
        c["url"] = f"https://www.instagram.com/p/{shortcode}/"
    return comments


def scrape_url_yt(url, max_comments=100, log=print):
    """Scrape comments from a single YouTube video URL.

    Robust terhadap layout A/B YouTube: parse ytInitialData sendiri,
    ambil komentar via youtubei/v1/next (commentEntityPayload).
    """
    import re as _re
    import json as _json
    import time as _time
    import requests as _rq
    from itertools import chain

    vid_m = _re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", url)
    if not vid_m:
        raise RuntimeError("YT: URL video tidak dikenali")
    watch_url = f"https://www.youtube.com/watch?v={vid_m.group(1)}"

    headers = {"User-Agent": UA, "Accept-Language": "id-ID,id;q=0.9,en;q=0.8"}

    def walk(obj, key):
        """Yield semua value dengan key tertentu di JSON nested."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key:
                    yield v
                yield from walk(v, key)
        elif isinstance(obj, list):
            for v in obj:
                yield from walk(v, key)

    def _likes_int(s):
        s = (s or "0").strip()
        try:
            if s.endswith("K"):
                return int(float(s[:-1]) * 1_000)
            if s.endswith("Jt") or s.endswith("M"):
                return int(float(s[:-2] if s.endswith("Jt") else s[:-1]) * 1_000_000)
            return int(s.replace(".", "").replace(",", ""))
        except ValueError:
            return 0

    last_err = None
    for attempt in range(3):
        rows = []
        try:
            s = _rq.Session()
            s.headers.update(headers)
            r = s.get(watch_url, timeout=30)
            r.raise_for_status()
            html = r.text

            key_m = _re.search(r'"INNERTUBE_API_KEY":"([\w-]+)"', html)
            ver_m = _re.search(r'"INNERTUBE_CLIENT_VERSION":"([\d.]+)"', html)
            if not key_m:
                raise RuntimeError("INNERTUBE_API_KEY tidak ditemukan")
            ytcfg = {
                "INNERTUBE_API_KEY": key_m.group(1),
                "INNERTUBE_CONTEXT": {"client": {
                    "clientName": "WEB",
                    "clientVersion": ver_m.group(1) if ver_m else "2.20261009.01.00",
                    "hl": "id", "gl": "ID",
                }},
            }

            m = (_re.search(r"var ytInitialData\s*=\s*({.+?});</script>", html, _re.S)
                 or _re.search(r'window\["ytInitialData"\]\s*=\s*({.+?});', html, _re.S))
            if not m:
                raise RuntimeError("ytInitialData tidak ditemukan")
            data = _json.loads(m.group(1))

            # Endpoint komentar: dari sort menu (index 1 = Terbaru), fallback
            # ke continuation pertama dari itemSection manapun.
            sm = next(walk(data, "sortFilterSubMenuRenderer"), {})
            sub = sm.get("subMenuItems") or []
            eps = [x.get("serviceEndpoint") for x in sub if x.get("serviceEndpoint")]
            cont_ep = eps[1] if len(eps) > 1 else (eps[0] if eps else None)
            if cont_ep is None:
                for sec in walk(data, "itemSectionRenderer"):
                    for cir in walk(sec, "continuationItemRenderer"):
                        ep = cir.get("continuationEndpoint")
                        if ep:
                            cont_ep = ep
                            break
                    if cont_ep:
                        break
            if cont_ep is None:
                raise RuntimeError("endpoint komentar tidak ditemukan")

            api_url = "https://www.youtube.com" + \
                cont_ep["commandMetadata"]["webCommandMetadata"]["apiUrl"]
            continuations = [cont_ep]
            pages = 0
            while continuations and len(rows) < max_comments and pages < 40:
                ep = continuations.pop()
                token = ep.get("continuationCommand", {}).get("token") or \
                    ep.get("continuation", {}).get("token", "")
                body = {"context": ytcfg.get("INNERTUBE_CONTEXT", {}), "continuation": token}
                resp = s.post(api_url, params={"key": ytcfg["INNERTUBE_API_KEY"]},
                              json=body, timeout=30)
                if resp.status_code != 200:
                    break
                rj = resp.json()

                for c in walk(rj, "commentEntityPayload"):
                    props = c.get("properties", {}) or {}
                    author = c.get("author", {}) or {}
                    toolbar = c.get("toolbar", {}) or {}
                    t = (props.get("content", {}) or {}).get("content") or ""
                    if not t:
                        continue
                    rows.append({
                        "source": "youtube",
                        "text": t.replace("\n", " ").strip()[:3000],
                        "author": author.get("displayName", "") or "",
                        "date": props.get("publishedTime", "") or "",
                        "likes": _likes_int(toolbar.get("likeCountNotliked", "0")),
                        "url": watch_url,
                    })
                    if len(rows) >= max_comments:
                        break

                if len(rows) < max_comments:
                    actions = chain(walk(rj, "reloadContinuationItemsCommand"),
                                    walk(rj, "appendContinuationItemsAction"))
                    for a in actions:
                        if a.get("targetId") in ("comments-section",
                                                 "engagement-panel-comments-section",
                                                 "shorts-engagement-panel-comments-section"):
                            for item in a.get("continuationItems", []):
                                for nep in walk(item, "continuationEndpoint"):
                                    continuations.insert(0, nep)
                    pages += 1
                _time.sleep(0.1)

            if rows:
                log(f"YT URL: {len(rows)} komentar")
                return rows[:max_comments]
            # Server jawab normal tapi tidak ada komentar -> kemungkinan besar
            # komentar dinonaktifkan/dibatasi utk video ini. Jangan retry.
            log("YT URL: tidak ada komentar yang bisa diakses")
            raise RuntimeError(
                "Tidak ada komentar yang bisa diakses untuk video ini "
                "(komentar mungkin dinonaktifkan oleh pembuat video).")
        except RuntimeError as e:
            last_err = e
        except Exception as e:
            last_err = RuntimeError(f"YT: {type(e).__name__}: {str(e)[:150]}")
        _time.sleep(2)

    raise last_err or RuntimeError("YT: gagal scrape URL")


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
        # Scroll beberapa kali agar komentar termuat
        for _ in range(3):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(1500)
        # Expand comments
        for _ in range(5):
            btns = page.query_selector_all('[role="button"]:has-text("View more comments"), '
                                          '[role="button"]:has-text("Lihat komentar lainnya"), '
                                          '[role="button"]:has-text("View more replies"), '
                                          '[role="button"]:has-text("Balas lainnya")')
            if not btns:
                break
            for b in btns[:3]:
                try:
                    b.click(timeout=3000)
                    page.wait_for_timeout(1200)
                except Exception:
                    pass

        # Extract comments (aria-label: "Comment by <nama> <waktu>" / "Komentar oleh ...")
        import re as _re
        comment_els = page.query_selector_all(
            '[aria-label^="Comment by"], [aria-label^="Komentar oleh"]')
        seen = set()
        for el in comment_els:
            if len(rows) >= max_comments:
                break
            try:
                text = el.inner_text().strip().replace("\n", " ")
                if len(text) < 5:
                    continue
                key = _re.sub(r"\s+", " ", text)[:200]
                if key in seen:
                    continue
                seen.add(key)
                label = el.get_attribute("aria-label") or ""
                author = _re.sub(r"^(Comment by|Komentar oleh)\s+", "", label)
                author = _re.sub(r"\s+(?:a|an|\d+|se)\s*\S*\s*(?:\w+\s+)?(?:ago|lalu)$", "", author).strip()
                rows.append({
                    "source": "facebook",
                    "text": text[:3000],
                    "author": author[:100],
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

    # Extract video ID from URL (support /video/<id> and short links vto.toktok etc.)
    import re as _re
    match = _re.search(r"/video/(\d+)", url)
    if not match:
        # vt.tiktok.com short URL → resolve via TikTokApi oEmbed or redirect
        try:
            import requests as _rq
            r = _rq.head(url, allow_redirects=True, timeout=15,
                         headers={"User-Agent": UA})
            url = r.url
            match = _re.search(r"/video/(\d+)", url)
        except Exception:
            pass
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
    """Fetch and extract text from a single web/news article URL.
    `max_comments` tidak relevan untuk artikel — 1 URL = 1 baris artikel.
    Extract juga tanggal publish + nama media bila tersedia."""
    import trafilatura
    from datetime import datetime, timezone
    from email.utils import parsedate_to_datetime

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

    # --- metadata extraction (best effort) ---
    date = ""
    try:
        meta = trafilatura.baseline(html) or {}
        raw_date = meta.get("date") or ""
        if raw_date:
            date = str(raw_date)[:10]
    except Exception:
        pass
    if not date:
        # <meta property="article:published_time" content="...">
        m = re.search(r'property=["\']article:published_time["\']\s+content=["\']([^"\']+)', html)
        if not m:
            m = re.search(r'name=["\'](?:pubdate|publishdate|date)["\']\s+content=["\']([^"\']+)', html)
        if m:
            date = m.group(1)[:10]

    author = ""
    try:
        m = re.search(r'property=["\']og:site_name["\']\s+content=["\']([^"\']+)', html)
        if m:
            author = m.group(1).strip()
    except Exception:
        pass
    if not author:
        try:
            from urllib.parse import urlparse
            author = urlparse(final_url).netloc.replace("www.", "")
        except Exception:
            author = ""

    log(f"Web URL: {len(text)} karakter diambil (media: {author or '?'}, tanggal: {date or '?'})")
    return [{
        "source": "web",
        "text": text[:6000],
        "author": author,
        "date": date,
        "likes": 0,
        "url": final_url,
    }]


def scrape_url_playstore(url, max_comments=100, log=print):
    """Scrape reviews dari satu app Play Store.
    URL: https://play.google.com/store/apps/details?id=<package>"""
    import re as _re
    from google_play_scraper import reviews, Sort

    m = _re.search(r"[?&]id=([a-zA-Z0-9._]+)", url)
    if not m:
        raise RuntimeError(f"URL Play Store tidak valid (butuh ?id=<package>): {url}")
    pkg = m.group(1)

    rows = []
    try:
        result, _ = reviews(
            pkg, lang="id", country="id",
            sort=Sort.NEWEST, count=max_comments,
        )
        for r in result:
            text = (r.get("content") or "").strip().replace("\n", " ")
            if len(text) < 3:
                continue
            rows.append({
                "source": "playstore",
                "text": text[:3000],
                "author": r.get("userName", ""),
                "date": r.get("at").isoformat() if r.get("at") else "",
                "likes": r.get("thumbsUpCount", 0) or 0,
                "url": f"https://play.google.com/store/apps/details?id={pkg}",
                "rating": r.get("score", ""),
            })
        log(f"Play Store URL: {pkg}: +{len(rows)} reviews")
    except Exception as e:
        raise RuntimeError(f"Play Store: gagal scrape {pkg}: {type(e).__name__} {str(e)[:120]}")
    return rows


URL_SCRAPERS = {
    "instagram": scrape_url_ig,
    "youtube": scrape_url_yt,
    "facebook": scrape_url_facebook,
    "tiktok": scrape_url_tiktok,
    "web": scrape_url_web,
    "playstore": scrape_url_playstore,
}
