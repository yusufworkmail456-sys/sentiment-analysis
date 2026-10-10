"""API routes for scraping."""
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import math

router = APIRouter(tags=["scrape"])

# Thread pool for blocking scrapers
_executor = ThreadPoolExecutor(max_workers=4)


class ScrapeKeywordRequest(BaseModel):
    keyword: str
    ig: int = 0
    yt: int = 0
    web: int = 0
    playstore: int = 0
    facebook: int = 0
    tiktok: int = 0
    detect_bots: bool = False
    tag_entities: bool = False


class ScrapeUrlRequest(BaseModel):
    url: str
    source: str  # instagram | youtube | playstore | facebook | tiktok | web
    limit: int = 100
    detect_bots: bool = False
    tag_entities: bool = False


def _df_to_records(df) -> list:
    """Convert DataFrame to JSON-safe list of dicts (handle NaN, NaT, Timestamp)."""
    import pandas as pd
    import math as _math

    records = []
    for row in df.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            if v is None:
                clean[k] = None
            elif isinstance(v, float) and _math.isnan(v):
                clean[k] = None
            elif hasattr(v, "isoformat"):          # datetime / Timestamp
                clean[k] = v.isoformat()
            elif isinstance(v, bool):
                clean[k] = v
            else:
                try:
                    clean[k] = str(v) if not isinstance(v, (int, float, str)) else v
                except Exception:
                    clean[k] = None
        records.append(clean)
    return records


def _run_scrape_keyword(req: ScrapeKeywordRequest):
    """Blocking function — runs in thread pool."""
    import pandas as pd
    from multiscrape import dedupe, scrape_ig, scrape_yt, scrape_web
    from scrapers_extra import scrape_facebook, scrape_tiktok, scrape_playstore
    from core import run_sentiment, OUT_DIR
    from datetime import datetime, timezone

    rows = []
    logs = []

    def log(msg):
        logs.append(str(msg))

    def ambil(name, fn, n):
        if n <= 0:
            return
        log(f"> {name}: mulai (target {n})...")
        try:
            got = fn(req.keyword.strip(), n, log)
            rows.extend(got)
            log(f"OK {name}: {len(got)} baris")
        except Exception as e:
            log(f"FAIL {name}: {type(e).__name__} {str(e)[:200]}")

    t0 = time.time()
    if req.ig > 0:        ambil("Instagram",  scrape_ig,        req.ig)
    if req.yt > 0:        ambil("YouTube",    scrape_yt,        req.yt)
    if req.web > 0:       ambil("Web",        scrape_web,       req.web)
    if req.playstore > 0: ambil("Play Store", scrape_playstore, req.playstore)
    if req.facebook > 0:  ambil("Facebook",   scrape_facebook,  req.facebook)
    if req.tiktok > 0:    ambil("TikTok",     scrape_tiktok,    req.tiktok)

    rows = dedupe(rows)
    if not rows:
        return {"ok": False, "error": "Tidak ada data terkumpul. Cek kredensial atau keyword.", "logs": logs}

    df = pd.DataFrame(rows)
    # Ensure required columns exist
    for col in ["text", "source", "author", "date", "likes", "url"]:
        if col not in df.columns:
            df[col] = ""
    df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0).astype(int)

    df = run_sentiment(df, detect_bots=req.detect_bots, tag_entities=req.tag_entities)

    stamp   = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_csv = OUT_DIR / f"sentiment_{req.keyword.strip().replace(' ','_')}_{stamp}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")

    return {
        "ok": True,
        "rows": _df_to_records(df),
        "meta": {
            "keyword": req.keyword.strip(),
            "stamp": stamp,
            "durasi": round(time.time() - t0),
            "mode": "keyword",
            "out_csv": str(out_csv),
        },
        "logs": logs,
    }


def _run_scrape_url(req: ScrapeUrlRequest):
    """Blocking function — runs in thread pool."""
    import pandas as pd
    from multiscrape import URL_SCRAPERS
    from core import run_sentiment, OUT_DIR
    from datetime import datetime, timezone

    scraper = URL_SCRAPERS.get(req.source)
    if not scraper:
        return {"ok": False, "error": f"Source '{req.source}' tidak didukung", "logs": []}

    logs = []

    def log(msg):
        logs.append(str(msg))

    t0 = time.time()
    try:
        rows = scraper(req.url.strip(), req.limit, log)
    except RuntimeError as e:
        return {"ok": False, "error": str(e), "logs": logs}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}", "logs": logs}

    if not rows:
        return {"ok": False, "error": "Tidak ada komentar terkumpul", "logs": logs}

    df = pd.DataFrame(rows)
    for col in ["text", "source", "author", "date", "likes", "url"]:
        if col not in df.columns:
            df[col] = ""
    df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0).astype(int)

    df = run_sentiment(df, detect_bots=req.detect_bots, tag_entities=req.tag_entities)

    stamp   = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_csv = OUT_DIR / f"sentiment_{req.source}_url_{stamp}.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")

    return {
        "ok": True,
        "rows": _df_to_records(df),
        "meta": {
            "keyword": req.url[:80],
            "stamp": stamp,
            "durasi": round(time.time() - t0),
            "mode": "url",
            "source": req.source,
            "out_csv": str(out_csv),
        },
        "logs": logs,
    }


@router.post("/scrape/keyword")
async def scrape_keyword(req: ScrapeKeywordRequest):
    """Scrape by keyword across platforms, run sentiment. Non-blocking via thread pool."""
    if not req.keyword.strip():
        raise HTTPException(400, "keyword kosong")
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(_executor, _run_scrape_keyword, req)
    except Exception as e:
        return {"ok": False, "error": f"Server error: {type(e).__name__}: {str(e)[:300]}", "logs": []}
    return result


@router.post("/scrape/url")
async def scrape_url(req: ScrapeUrlRequest):
    """Scrape a single post URL, run sentiment. Non-blocking via thread pool."""
    if not req.url.strip():
        raise HTTPException(400, "URL kosong")
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(_executor, _run_scrape_url, req)
    except Exception as e:
        return {"ok": False, "error": f"Server error: {type(e).__name__}: {str(e)[:300]}", "logs": []}
    return result
