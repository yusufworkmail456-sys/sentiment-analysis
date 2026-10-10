#!/usr/bin/env python3
"""Sentix AI – FastAPI entrypoint.

Jalankan:
  ./venv/bin/uvicorn main:app --host 127.0.0.1 --port 9120 --reload
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config  # noqa: E402  (loads .env)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Sentix AI", version="2.0.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": str(exc), "traceback": tb},
    )

# ── API routers ───────────────────────────────────────────────────────────
from api.scrape    import router as scrape_router    # noqa: E402
from api.sentiment import router as sentiment_router  # noqa: E402
from api.ai        import router as ai_router         # noqa: E402
from api.export    import router as export_router     # noqa: E402
from api.sessions  import router as sessions_router   # noqa: E402

app.include_router(scrape_router,    prefix="/api")
app.include_router(sentiment_router, prefix="/api")
app.include_router(ai_router,        prefix="/api")
app.include_router(export_router,    prefix="/api")
app.include_router(sessions_router,  prefix="/api")

# ── Static files ──────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/index.html")

# Catch-all for SPA routing
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    return FileResponse("static/index.html")
