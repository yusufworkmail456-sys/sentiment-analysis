"""API routes for scrape history (raw results + logs), retention 6 hours."""
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(tags=["history"])

HISTORY_DIR = Path(__file__).parent.parent / "hasil" / "history"
RETENTION_SECONDS = 6 * 3600  # 6 jam
MAX_FILES = 50                # hard cap supaya disk aman


def _cleanup():
    """Buang history lebih tua dari 6 jam + cap jumlah file."""
    if not HISTORY_DIR.exists():
        return
    now = time.time()
    files = sorted(HISTORY_DIR.glob("history_*.json"))
    for f in files:
        try:
            if now - f.stat().st_mtime > RETENTION_SECONDS:
                f.unlink(missing_ok=True)
        except Exception:
            pass
    # cap: sisakan file terbaru
    files = sorted(HISTORY_DIR.glob("history_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[MAX_FILES:]:
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


def save_history(kind: str, label: str, meta: dict, logs: list, rows: list) -> str:
    """Simpan hasil lengkap + logs. Dipanggil dari api/scrape.py. Return history_id."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup()
    ts = datetime.now(timezone.utc)
    hid = ts.strftime("%Y%m%d-%H%M%S")
    payload = {
        "id": hid,
        "kind": kind,                       # keyword | url
        "label": label,                     # keyword atau url
        "created": ts.isoformat(),
        "created_epoch": ts.timestamp(),
        "expires_epoch": ts.timestamp() + RETENTION_SECONDS,
        "meta": meta,
        "logs": logs,
        "rows": rows,
        "row_count": len(rows),
    }
    path = HISTORY_DIR / f"history_{hid}_{kind}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return hid


def _read_history(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/history")
async def list_history():
    """Daftar riwayat scrape (tanpa rows — ringan)."""
    _cleanup()
    items = []
    if HISTORY_DIR.exists():
        for f in sorted(HISTORY_DIR.glob("history_*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            h = _read_history(f)
            if not h:
                continue
            items.append({
                "id": h.get("id"),
                "kind": h.get("kind"),
                "label": h.get("label"),
                "created": h.get("created"),
                "row_count": h.get("row_count", 0),
                "expires_epoch": h.get("expires_epoch"),
                "meta": h.get("meta", {}),
            })
    return {"ok": True, "items": items, "retention_hours": 6}


@router.get("/history/{hid}")
async def get_history(hid: str):
    """Satu riwayat lengkap (rows + logs) — dipakai untuk muat ulang hasil."""
    _cleanup()
    matches = list(HISTORY_DIR.glob(f"history_{hid}_*.json"))
    if not matches:
        raise HTTPException(404, "Riwayat tidak ditemukan (mungkin sudah >6 jam)")
    h = _read_history(matches[0])
    if not h:
        raise HTTPException(500, "File riwayat rusak")
    return {"ok": True, **h}


@router.get("/history/{hid}/csv")
async def history_csv(hid: str):
    """Download CSV mentah dari riwayat (semua kolom, tanpa re-analisis)."""
    import io
    import csv as _csv

    _cleanup()
    matches = list(HISTORY_DIR.glob(f"history_{hid}_*.json"))
    if not matches:
        raise HTTPException(404, "Riwayat tidak ditemukan (mungkin sudah >6 jam)")
    h = _read_history(matches[0]) or {}
    rows = h.get("rows", [])
    if not rows:
        return Response(content=b"", status_code=404)

    cols = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)

    buf = io.StringIO()
    w = _csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    label = (h.get("label") or "hasil").replace(" ", "_")[:40]
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="raw_{label}_{hid}.csv"'},
    )


@router.delete("/history/{hid}")
async def delete_history(hid: str):
    matches = list(HISTORY_DIR.glob(f"history_{hid}_*.json"))
    if not matches:
        raise HTTPException(404, "Tidak ditemukan")
    matches[0].unlink(missing_ok=True)
    return {"ok": True}
