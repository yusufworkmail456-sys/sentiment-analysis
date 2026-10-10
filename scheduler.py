"""Scheduler scrape terjadwal (APScheduler) — dijalankan di dalam proses FastAPI.

Default: keyword 'taspen' tiap 6 jam. Konfigurasi via .env:
  SCHEDULE_KEYWORDS=taspen,taspen life
  SCHEDULE_INTERVAL_HOURS=6
  SCHEDULE_ENABLED=1
Hasil masuk DB (db_store.save_run) + CSV, sama seperti scrape manual.
"""
import os
import threading
import traceback
from datetime import datetime, timezone

_scheduler = None
_started = False


def _get_env(name, default):
    try:
        import config
        return getattr(config, name, default)
    except Exception:
        return default


def _run_scheduled(keyword: str):
    """Scrape satu keyword (paket default) → DB. Dipanggil scheduler."""
    try:
        import pandas as pd
        from api.scrape import _df_to_records
        from multiscrape import dedupe, scrape_ig, scrape_web, scrape_yt
        from scrapers_extra import scrape_playstore
        from core import run_sentiment
        from db_store import save_run
        from pathlib import Path
        import config as _config

        targets = {"YouTube": 30, "Web": 8, "Play Store": 30}
        rows, logs = [], []

        def log(msg):
            logs.append(str(msg))

        def ambil(name, fn, n):
            log(f"> {name}: target {n}")
            try:
                got = fn(keyword, n, log)
                rows.extend(got)
                log(f"OK {name}: {len(got)}/{n}")
            except Exception as e:
                log(f"FAIL {name}: {type(e).__name__} {str(e)[:150]}")

        t0 = datetime.now(timezone.utc)
        ambil("YouTube", scrape_yt, targets["YouTube"])
        ambil("Web", scrape_web, targets["Web"])
        ambil("Play Store", scrape_playstore, targets["Play Store"])

        rows = dedupe(rows)
        if not rows:
            log("scheduled: tidak ada data")
            _write_sched_log(keyword, logs, 0)
            return
        df = pd.DataFrame(rows)
        for col in ["text", "source", "author", "date", "likes", "url"]:
            if col not in df.columns:
                df[col] = ""
        df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0).astype(int)
        df = run_sentiment(df, detect_bots=True, tag_entities=True)
        records = _df_to_records(df)

        stats = save_run("keyword", keyword, targets, records, {
            "durasi": (datetime.now(timezone.utc) - t0).seconds,
        }, logs)

        # CSV arsip (sama format dengan manual)
        from core import OUT_DIR
        stamp = t0.strftime("%Y%m%d-%H%M%S")
        out_csv = OUT_DIR / f"scheduled_{keyword.strip().replace(' ', '_')}_{stamp}.csv"
        df.to_csv(out_csv, index=False, encoding="utf-8")

        log(f"scheduled selesai: run#{stats['run_id']} new={stats['new']} dup={stats['dup']} GSS={stats['gss']}")
        _write_sched_log(keyword, logs, len(records))
    except Exception:
        tb = traceback.format_exc()
        _write_sched_log(keyword, [f"FATAL {type(e).__name__ if (e:=None) is None else ''}" if False else "FATAL"] + tb.splitlines()[-6:], 0)


def _write_sched_log(keyword: str, logs: list, rows: int):
    """Log ringkas ke hasil/scheduler.log."""
    from core import OUT_DIR
    try:
        with open(OUT_DIR / "scheduler.log", "a", encoding="utf-8") as f:
            f.write(f"=== {datetime.now(timezone.utc).isoformat()} keyword={keyword} rows={rows} ===\n")
            for l in logs[-25:]:
                f.write(f"  {l}\n")
    except Exception:
        pass


def start_scheduler(app=None):
    """Mulai scheduler bila SCHEDULE_ENABLED != 0. Idempotent."""
    global _scheduler, _started
    if _started:
        return
    enabled = str(_get_env("SCHEDULE_ENABLED", "1"))
    if enabled.strip().lower() in ("0", "false", "no"):
        print("[scheduler] disabled via SCHEDULE_ENABLED=0")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        print("[scheduler] apscheduler tidak terpasang — skip (pip install apscheduler)")
        return

    keywords = [k.strip() for k in str(_get_env("SCHEDULE_KEYWORDS", "taspen")).split(",") if k.strip()]
    try:
        hours = float(_get_env("SCHEDULE_INTERVAL_HOURS", "6"))
    except Exception:
        hours = 6.0

    _scheduler = BackgroundScheduler(timezone="UTC")
    for kw in keywords:
        _scheduler.add_job(
            _run_scheduled, "interval", hours=hours, args=[kw],
            id=f"sched_{kw}", next_run_time=datetime.now(timezone.utc),  # langsung jalan sekali saat start
        )
    _scheduler.start()
    _started = True
    print(f"[scheduler] aktif: keywords={keywords} interval={hours}h")
