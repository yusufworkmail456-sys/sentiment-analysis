#!/usr/bin/env python3
"""SQLite store untuk Historical Analytics.

Tabel:
- scrape_runs : 1 baris per scrape keyword (metrik agregat — tulang punggung time series)
- comments    : komentar unik global (dedup via content_hash UNIQUE)

Dedup: content_hash = sha1(source + author + normalize(text)), UNIQUE lintas run.
Baris duplikat TIDAK diinsert; last_seen/times_seen/likes_max di-update.
"""
import hashlib
import json
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "hasil" / "taspen_sentiment.db"
DB_PATH.parent.mkdir(exist_ok=True)

_lock = threading.Lock()  # SQLite: satu writer pada satu waktu


def _conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _normalize_text(t: str) -> str:
    """Normalisasi teks untuk dedup: lowercase, buang spasi/punct berlebih."""
    t = (t or "").lower()
    t = re.sub(r"https?://\S+", "", t)          # URL dianggap noise
    t = re.sub(r"[^a-z0-9à-ÿ\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def content_hash(source: str, author: str, text: str) -> str:
    raw = f"{(source or '').strip().lower()}|{(author or '').strip().lower()}|{_normalize_text(text)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,                -- ISO UTC waktu scrape
    ts_epoch      REAL NOT NULL,
    mode          TEXT NOT NULL DEFAULT 'keyword',
    keyword       TEXT NOT NULL,
    targets_json  TEXT DEFAULT '{}',
    gss           REAL,                         -- 0..100
    nss           REAL,                         -- -100..+100
    pos           INTEGER DEFAULT 0,
    neu           INTEGER DEFAULT 0,
    neg           INTEGER DEFAULT 0,
    total_rows    INTEGER DEFAULT 0,            -- baris hasil run (setelah dedupe)
    new_count     INTEGER DEFAULT 0,            -- komentar baru (belum ada di DB)
    dup_count     INTEGER DEFAULT 0,            -- duplikat (sudah pernah ada)
    sources_json  TEXT DEFAULT '{}',            -- {source: n}
    durasi        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_runs_kw_ts ON scrape_runs(keyword, ts_epoch);

CREATE TABLE IF NOT EXISTS comments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash      TEXT NOT NULL UNIQUE,
    source            TEXT NOT NULL,
    text              TEXT NOT NULL,
    author            TEXT DEFAULT '',
    date_raw          TEXT DEFAULT '',           -- tanggal komentar dari platform (boleh kosong)
    date_epoch        REAL,                      -- epoch dari date_raw bila parseable
    likes             INTEGER DEFAULT 0,
    likes_max         INTEGER DEFAULT 0,
    url               TEXT DEFAULT '',
    label             TEXT DEFAULT '',
    score             REAL DEFAULT 0,
    kategori          TEXT DEFAULT '',
    is_bot_suspect    INTEGER,                   -- 0/1/NULL
    bot_reasons       TEXT DEFAULT '',
    entity_mentions   TEXT DEFAULT '',
    entity_categories TEXT DEFAULT '',
    run_id_first      INTEGER,                   -- run pertama kali komentar ini muncul
    first_seen        TEXT NOT NULL,
    first_seen_epoch  REAL NOT NULL,
    last_seen         TEXT NOT NULL,
    times_seen        INTEGER DEFAULT 1,
    FOREIGN KEY (run_id_first) REFERENCES scrape_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_cmt_kw ON comments(run_id_first);
CREATE INDEX IF NOT EXISTS idx_cmt_date ON comments(date_epoch);
CREATE INDEX IF NOT EXISTS idx_cmt_source ON comments(source);
"""


def init_db():
    with _lock, _conn() as c:
        c.executescript(SCHEMA)


# ---------------------------------------------------------------- write path
def save_run(mode: str, keyword: str, targets: dict, rows: list, meta: dict, logs: list) -> dict:
    """Simpan 1 run + upsert komentar-unik. Return statistik run.
    rows = list of dict hasil sentiment (kolom label/score/kategori dsb sudah ada).
    """
    init_db()
    now = datetime.now(timezone.utc)
    total = len(rows)
    pos = sum(1 for r in rows if r.get("label") == "Positif")
    neu = sum(1 for r in rows if r.get("label") == "Netral")
    neg = sum(1 for r in rows if r.get("label") == "Negatif")
    gss = round((pos + 0.5 * neu) / total * 100, 2) if total else 50.0
    nss = round(pos - neg, 2)  # dalam persen poin
    per_src = {}
    for r in rows:
        per_src[r.get("source", "?")] = per_src.get(r.get("source", "?"), 0) + 1

    with _lock, _conn() as c:
        cur = c.execute(
            """INSERT INTO scrape_runs
               (ts, ts_epoch, mode, keyword, targets_json, gss, nss, pos, neu, neg,
                total_rows, new_count, dup_count, sources_json, durasi)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (now.isoformat(), now.timestamp(), mode, keyword,
             json.dumps(targets or {}), gss, nss, pos, neu, neg,
             total, 0, 0, json.dumps(per_src), int(meta.get("durasi") or 0)),
        )
        run_id = cur.lastrowid

        new_count, dup_count = 0, 0
        for r in rows:
            ch = content_hash(r.get("source", ""), r.get("author", ""), r.get("text", ""))
            date_epoch = _parse_date_epoch(r.get("date", ""))
            likes = int(r.get("likes") or 0)
            bot = r.get("is_bot_suspect")
            bot_int = None if bot is None or bot == "" else (1 if str(bot).lower() in ("1", "true") else 0)
            existing = c.execute(
                "SELECT id, likes_max, times_seen FROM comments WHERE content_hash=?", (ch,)
            ).fetchone()
            if existing:
                dup_count += 1
                c.execute(
                    """UPDATE comments SET last_seen=?, times_seen=times_seen+1,
                       likes_max=MAX(?, likes_max) WHERE id=?""",
                    (now.isoformat(), likes, existing["id"]),
                )
            else:
                new_count += 1
                c.execute(
                    """INSERT INTO comments
                       (content_hash, source, text, author, date_raw, date_epoch,
                        likes, likes_max, url, label, score, kategori,
                        is_bot_suspect, bot_reasons, entity_mentions, entity_categories,
                        run_id_first, first_seen, first_seen_epoch, last_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ch, r.get("source", ""), r.get("text", ""), r.get("author", ""),
                     r.get("date", "") or "", date_epoch,
                     likes, likes, r.get("url", ""),
                     r.get("label", ""), float(r.get("score") or 0), r.get("kategori", ""),
                     bot_int, r.get("bot_reasons", "") or "",
                     r.get("entity_mentions", "") or "", r.get("entity_categories", "") or "",
                     run_id, now.isoformat(), now.timestamp(), now.isoformat()),
                )
        c.execute("UPDATE scrape_runs SET new_count=?, dup_count=? WHERE id=?",
                  (new_count, dup_count, run_id))

    return {
        "run_id": run_id, "ts": now.isoformat(), "gss": gss, "nss": nss,
        "total": total, "new": new_count, "dup": dup_count,
        "pos": pos, "neu": neu, "neg": neg, "per_source": per_src,
    }


def _parse_date_epoch(raw: str):
    if not raw:
        return None
    try:
        from datetime import datetime as dt
        parsed = dt.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except Exception:
        return None


# ----------------------------------------------------------------- read path
def list_runs(keyword=None, since_epoch=None, limit=500) -> list:
    init_db()
    q = "SELECT * FROM scrape_runs WHERE 1=1"
    args = []
    if keyword:
        q += " AND keyword=?"
        args.append(keyword)
    if since_epoch:
        q += " AND ts_epoch>=?"
        args.append(since_epoch)
    q += " ORDER BY ts_epoch ASC LIMIT ?"
    args.append(limit)
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def keywords_in_db() -> list:
    init_db()
    with _conn() as c:
        return [r["keyword"] for r in c.execute(
            "SELECT DISTINCT keyword FROM scrape_runs ORDER BY keyword")]


def comments_over_time(keyword=None, source=None, since_epoch=None, until_epoch=None,
                       bucket="day") -> list:
    """Komentar unik first_seen per bucket (day/month/year) — pertumbuhan data."""
    init_db()
    fmt = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}[bucket]
    q = f"""SELECT strftime('{fmt}', first_seen_epoch, 'unixepoch') AS bucket,
                   COUNT(*) AS n,
                   SUM(CASE WHEN label='Positif' THEN 1 ELSE 0 END) AS pos,
                   SUM(CASE WHEN label='Netral'  THEN 1 ELSE 0 END) AS neu,
                   SUM(CASE WHEN label='Negatif' THEN 1 ELSE 0 END) AS neg
            FROM comments c WHERE 1=1"""
    args = []
    if keyword:
        q += " AND c.run_id_first IN (SELECT id FROM scrape_runs WHERE keyword=?)"
        args.append(keyword)
    if source:
        q += " AND c.source=?"
        args.append(source)
    if since_epoch:
        q += " AND first_seen_epoch>=?"
        args.append(since_epoch)
    if until_epoch:
        q += " AND first_seen_epoch<=?"
        args.append(until_epoch)
    q += " GROUP BY bucket ORDER BY bucket"
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def comment_date_series(keyword=None, source=None, since_epoch=None, until_epoch=None,
                        bucket="day") -> list:
    """Distribusi per tanggal komentar (date_epoch) — jenis B, hanya baris bertanggal."""
    init_db()
    fmt = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}[bucket]
    q = f"""SELECT strftime('{fmt}', date_epoch, 'unixepoch') AS bucket,
                   COUNT(*) AS n,
                   SUM(CASE WHEN label='Positif' THEN 1 ELSE 0 END) AS pos,
                   SUM(CASE WHEN label='Netral'  THEN 1 ELSE 0 END) AS neu,
                   SUM(CASE WHEN label='Negatif' THEN 1 ELSE 0 END) AS neg
            FROM comments c WHERE date_epoch IS NOT NULL AND 1=1"""
    args = []
    if keyword:
        q += " AND c.run_id_first IN (SELECT id FROM scrape_runs WHERE keyword=?)"
        args.append(keyword)
    if source:
        q += " AND c.source=?"
        args.append(source)
    if since_epoch:
        q += " AND date_epoch>=?"
        args.append(since_epoch)
    if until_epoch:
        q += " AND date_epoch<=?"
        args.append(until_epoch)
    q += " GROUP BY bucket ORDER BY bucket"
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def db_stats() -> dict:
    init_db()
    with _conn() as c:
        runs = c.execute("SELECT COUNT(*) AS n FROM scrape_runs").fetchone()["n"]
        kw = c.execute("SELECT COUNT(DISTINCT keyword) AS n FROM scrape_runs").fetchone()["n"]
        cmts = c.execute("SELECT COUNT(*) AS n FROM comments").fetchone()["n"]
        dated = c.execute("SELECT COUNT(*) AS n FROM comments WHERE date_epoch IS NOT NULL").fetchone()["n"]
        bots = c.execute("SELECT COUNT(*) AS n FROM comments WHERE is_bot_suspect=1").fetchone()["n"]
        ents = c.execute("SELECT COUNT(*) AS n FROM comments WHERE entity_categories != ''").fetchone()["n"]
        last = c.execute("SELECT ts FROM scrape_runs ORDER BY ts_epoch DESC LIMIT 1").fetchone()
    return {"runs": runs, "keywords": kw, "unique_comments": cmts,
            "dated_comments": dated, "bot_flagged": bots, "entity_rows": ents,
            "last_run": last["ts"] if last else None,
            "db_path": str(DB_PATH)}


def backfill_csv(csv_path: str, keyword: str) -> dict:
    """Backfill CSV hasil scrape lama ke DB (dedup global tetap berlaku).
    CSV dianggap 1 run historis dengan ts = mtime file."""
    import csv as _csv
    import pandas as pd

    df = pd.read_csv(csv_path)
    if "source" not in df.columns or "text" not in df.columns:
        return {"skipped": True, "reason": "kolom tidak lengkap"}
    now = datetime.now(timezone.utc)
    try:
        ts = datetime.fromtimestamp(Path(csv_path).stat().st_mtime, tz=timezone.utc)
    except Exception:
        ts = now

    rows = df.fillna("").to_dict(orient="records")
    with _lock, _conn() as c:
        cur = c.execute(
            """INSERT INTO scrape_runs
               (ts, ts_epoch, mode, keyword, targets_json, gss, nss, pos, neu, neg,
                total_rows, new_count, dup_count, sources_json, durasi)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ts.isoformat(), ts.timestamp(), "keyword", keyword, "{}",
             0, 0, 0, 0, 0, len(rows), 0, 0, "{}", 0),
        )
        run_id = cur.lastrowid
        new_count, dup_count = 0, 0
        pos = neu = neg = 0
        per_src = {}
        for r in rows:
            label = str(r.get("label", ""))
            per_src[r.get("source", "?")] = per_src.get(r.get("source", "?"), 0) + 1
            if label == "Positif": pos += 1
            elif label == "Netral": neu += 1
            elif label == "Negatif": neg += 1
            ch = content_hash(r.get("source", ""), r.get("author", ""), r.get("text", ""))
            date_epoch = _parse_date_epoch(r.get("date", ""))
            likes = int(float(r.get("likes") or 0))
            bot = r.get("is_bot_suspect", "")
            bot_int = None if bot in ("", None) else (1 if str(bot).lower() in ("1", "true") else 0)
            existing = c.execute("SELECT id FROM comments WHERE content_hash=?", (ch,)).fetchone()
            if existing:
                dup_count += 1
                c.execute("""UPDATE comments SET last_seen=?, times_seen=times_seen+1,
                             likes_max=MAX(?, likes_max) WHERE id=?""",
                          (ts.isoformat(), likes, existing["id"]))
            else:
                new_count += 1
                c.execute(
                    """INSERT INTO comments
                       (content_hash, source, text, author, date_raw, date_epoch,
                        likes, likes_max, url, label, score, kategori,
                        is_bot_suspect, bot_reasons, entity_mentions, entity_categories,
                        run_id_first, first_seen, first_seen_epoch, last_seen)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (ch, r.get("source", ""), str(r.get("text", "")), r.get("author", ""),
                     r.get("date", "") or "", date_epoch, likes, likes, r.get("url", ""),
                     label, float(r.get("score") or 0), r.get("kategori", ""),
                     bot_int, r.get("bot_reasons", "") or "",
                     r.get("entity_mentions", "") or "", r.get("entity_categories", "") or "",
                     run_id, ts.isoformat(), ts.timestamp(), ts.isoformat()),
                )
        gss = round((pos + 0.5 * neu) / len(rows) * 100, 2) if rows else 50.0
        c.execute("""UPDATE scrape_runs SET gss=?, nss=?, pos=?, neu=?, neg=?,
                     new_count=?, dup_count=?, sources_json=? WHERE id=?""",
                  (gss, round(pos - neg, 2), pos, neu, neg, new_count, dup_count,
                   json.dumps(per_src), run_id))
    return {"run_id": run_id, "rows": len(rows), "new": new_count, "dup": dup_count}


def historical_context(keyword=None, sample_n=25) -> str:
    """Context teks untuk LLM dari seluruh DB historis (token-aman, agregat + sampel).

    Isi: statistik umum, tren GSS antar run, distribusi sentimen per sumber,
    top entitas, top kategori, sampel komentar negatif/positif, topik kata.
    """
    import re as _re
    from collections import Counter
    from core import LABELS, top_terms

    init_db()
    kw_clause, kw_params = "", []          # utk scrape_runs (punya kolom keyword)
    kw_cmt, kw_cmt_params = "", []         # utk comments (via run_id_first → scrape_runs)
    if keyword:
        kw_clause = " WHERE keyword = ?"
        kw_params = [keyword]
        kw_cmt = " WHERE run_id_first IN (SELECT id FROM scrape_runs WHERE keyword = ?)"
        kw_cmt_params = [keyword]
    parts = ["=== KONTEKS SENTIMENT HISTORIS (database kumulatif, dedup global) ==="]
    with _conn() as c:
        # Ringkasan umum
        runs = c.execute(f"SELECT id, ts, keyword, gss, nss, pos, neu, neg, new_count, dup_count, sources_json FROM scrape_runs{kw_clause} ORDER BY ts_epoch", kw_params).fetchall()
        total_rows = c.execute(f"SELECT COUNT(*) AS n FROM comments{kw_cmt}", kw_cmt_params).fetchone()["n"]
        dated = c.execute(f"SELECT COUNT(*) AS n FROM comments{kw_cmt} {'AND' if kw_cmt else 'WHERE'} date_epoch IS NOT NULL", kw_cmt_params).fetchone()["n"]
        bots = c.execute(f"SELECT COUNT(*) AS n FROM comments{kw_cmt} {'AND' if kw_cmt else 'WHERE'} is_bot_suspect=1", kw_cmt_params).fetchone()["n"]
        parts.append(f"Keyword filter: {keyword or 'semua'} | Run tercatat: {len(runs)} | Komentar unik: {total_rows} | Dengan tanggal: {dated} | Dugaan bot: {bots}")
        if not runs:
            parts.append("Database kosong.")
            return "\n".join(parts)

        # Tren GSS antar run (maks 40 titik terakhir biar token aman)
        sub = runs[-40:]
        parts.append("\nTren GSS antar run (waktu → GSS, pos/neu/neg):")
        for r in sub:
            parts.append(f"  {r['ts'][:16]} | GSS {r['gss']:.1f} | P {r['pos']}/N {r['neu']}/Neg {r['neg']} | +{r['new_count']} baru/{r['dup_count']} dup")

        # Distribusi per sumber
        per_src = {}
        for r in runs:
            try:
                for s, d in json.loads(r["sources_json"] or "{}").items():
                    per_src.setdefault(s, Counter()).update(d)
            except Exception:
                pass
        if per_src:
            parts.append("\nDistribusi sentimen kumulatif per sumber:")
            for s, ctr in per_src.items():
                tot = sum(ctr.values())
                parts.append(f"  {s}: total {tot} → P {ctr.get('Positif',0)}, N {ctr.get('Netral',0)}, Neg {ctr.get('Negatif',0)}")

        # Top entitas & kategori
        for col, title in [("entity_mentions", "Top entitas/pihak terkait"), ("entity_categories", "Kategori entitas")]:
            cnt = Counter()
            for row in c.execute(f"SELECT {col} AS v FROM comments{kw_cmt}{' AND' if kw_cmt else ' WHERE'} {col} != ''", kw_cmt_params):
                for e in str(row["v"]).split(","):
                    e = e.strip()
                    if e:
                        cnt[e] += 1
            if cnt:
                parts.append(f"\n{title}: " + ", ".join(f"{k}({v})" for k, v in cnt.most_common(12)))

        # Kategori × sentimen
        cat = c.execute(f"""SELECT kategori AS k, label AS l, COUNT(*) AS n FROM comments{kw_cmt}
                            GROUP BY kategori, label ORDER BY n DESC LIMIT 40""", kw_cmt_params).fetchall()
        if cat:
            parts.append("\nKategori × sentimen (atas):")
            for r in cat[:14]:
                parts.append(f"  {r['k']}: {r['l']} = {r['n']}")

        # Sampel komentar (negatif & positif teratas)
        for lab, title in [("Negatif", "Sampel komentar NEGATIF"), ("Positif", "Sampel komentar POSITIF")]:
            rows = c.execute(f"""SELECT text, author, source, likes FROM comments{kw_cmt}
                                 {'AND' if kw_cmt else 'WHERE'} label = ?
                                 ORDER BY likes DESC, first_seen DESC LIMIT ?""",
                             kw_cmt_params + [lab, sample_n]).fetchall()
            if rows:
                parts.append(f"\n{title} (by engagement):")
                for r in rows[:sample_n]:
                    parts.append(f"  [{r['source']}] ({r['author']}, likes={r['likes']}): {str(r['text'])[:180]}")

    # Topik kata dari sampel DB ringan
    try:
        import pandas as pd
        with _conn() as c:
            neg_t = [r["text"] for r in c.execute(f"SELECT text FROM comments{kw_cmt}{' AND' if kw_cmt else ' WHERE'} label='Negatif'", kw_cmt_params).fetchall()[:500]]
            pos_t = [r["text"] for r in c.execute(f"SELECT text FROM comments{kw_cmt}{' AND' if kw_cmt else ' WHERE'} label='Positif'", kw_cmt_params).fetchall()[:500]]
        kw_terms = set(_re.findall(r"[a-zA-Zà-ÿ']{3,}", str(keyword or "").lower()))
        if len(neg_t) >= 3:
            parts.append(f"\nTopik negatif: {', '.join(f'{w}({n})' for w, n in top_terms(neg_t, 6, exclude=kw_terms))}")
        if len(pos_t) >= 3:
            parts.append(f"Topik positif: {', '.join(f'{w}({n})' for w, n in top_terms(pos_t, 6, exclude=kw_terms))}")
    except Exception:
        pass
    parts.append("\nCatatan: ini data KUMULATIF lintas waktu (bukan snapshot 1 scrape). Jika user tanya tren, lihat Tren GSS antar run.")
    parts.append("=== END ===")
    return "\n".join(parts)
