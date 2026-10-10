"""API routes untuk Historical Analytics (SQLite-backed)."""
import time
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["history"])


def _parse_dt(s: Optional[str]):
    """'2026-10-01' → epoch UTC; None kalau kosong/invalid."""
    if not s:
        return None
    try:
        from datetime import datetime, timezone
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.timestamp()
    except Exception:
        return None


@router.get("/analytics/overview")
async def analytics_overview():
    from db_store import db_stats
    return {"ok": True, **db_stats()}


@router.get("/analytics/runs")
async def analytics_runs(keyword: Optional[str] = None, days: Optional[int] = None):
    """Semua run ( ASC by time) — bahan chart utama."""
    from db_store import list_runs
    since = time.time() - days * 86400 if days else None
    runs = list_runs(keyword=keyword, since_epoch=since)
    for r in runs:
        r["targets"] = _safe_json(r.pop("targets_json", "{}"))
        r["sources"] = _safe_json(r.pop("sources_json", "{}"))
    return {"ok": True, "runs": runs}


@router.get("/analytics/growth")
async def analytics_growth(keyword: Optional[str] = None, source: Optional[str] = None,
                           bucket: str = "month"):
    """Komentar unik kumulatif + baru per bucket (first_seen)."""
    from db_store import comments_over_time
    if bucket not in ("day", "month", "year"):
        bucket = "month"
    data = comments_over_time(keyword=keyword, source=source, bucket=bucket)
    cumulative, cum = [], 0
    for d in data:
        cum += d["n"]
        cumulative.append({**d, "cum": cum})
    return {"ok": True, "series": cumulative, "bucket": bucket}


@router.get("/analytics/comment-dates")
async def analytics_comment_dates(keyword: Optional[str] = None, source: Optional[str] = None,
                                  bucket: str = "month"):
    """Jenis B: distribusi per tanggal komentar (hanya baris bertanggal)."""
    from db_store import comment_date_series
    if bucket not in ("day", "month", "year"):
        bucket = "month"
    data = comment_date_series(keyword=keyword, source=source, bucket=bucket)
    total_dated = sum(d["n"] for d in data)
    return {"ok": True, "series": data, "bucket": bucket, "total_dated": total_dated}


@router.get("/analytics/keywords")
async def analytics_keywords():
    from db_store import keywords_in_db
    return {"ok": True, "keywords": keywords_in_db()}


class BackfillRequest(BaseModel):
    keyword: str
    dry_run: bool = False


@router.post("/analytics/backfill")
async def analytics_backfill(req: BackfillRequest):
    """Backfill SEMUA CSV lama hasil/ untuk satu keyword (dedup global berlaku).
    Nama file: sentiment_<keyword>_<stamp>.csv atau scheduled_<keyword>_<stamp>.csv"""
    from pathlib import Path
    from db_store import backfill_csv, content_hash, init_db, DB_PATH

    hasil_dir = Path(__file__).parent.parent / "hasil"
    kw_norm = req.keyword.strip().lower().replace(" ", "_")
    candidates = sorted(hasil_dir.glob("*.csv"))
    matched = []
    for f in candidates:
        name = f.name.lower()
        if f"_{kw_norm}_" in name or name.startswith(f"{kw_norm}_"):
            matched.append(f)

    results, total_new = [], 0
    if not req.dry_run:
        init_db()
    for f in matched:
        if req.dry_run:
            try:
                import pandas as pd
                n = len(pd.read_csv(f))
            except Exception:
                n = 0
            results.append({"file": f.name, "rows": n, "dry": True})
            total_new += n
            continue
        try:
            r = backfill_csv(str(f), req.keyword.strip())
            results.append({"file": f.name, **r})
            total_new += r.get("new", 0)
        except Exception as e:
            results.append({"file": f.name, "error": f"{type(e).__name__}: {str(e)[:120]}"})

    return {"ok": True, "keyword": req.keyword, "files_matched": len(matched),
            "total_new": total_new, "dry_run": req.dry_run, "results": results}


def _safe_json(s: str) -> dict:
    import json
    try:
        return json.loads(s or "{}")
    except Exception:
        return {}
