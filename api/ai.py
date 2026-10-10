"""API routes for AI insight: executive summary, recommendations, chatbot.

Semua endpoint menerima `mode`:
- "session"    (default): analisis snapshot scrape terakhir (App.state.rows)
- "historical": analisis kumulatif dari database (dedup global, semua run)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(tags=["ai"])


class InsightRequest(BaseModel):
    rows: list = []
    meta: dict = {}
    mode: str = "session"           # session | historical
    keyword: Optional[str] = None   # filter DB utk mode historical


class ChatMessage(BaseModel):
    role: str           # user | assistant
    content: str


class ChatRequest(BaseModel):
    rows: list = []
    meta: dict = {}
    messages: List[ChatMessage] = []
    user_input: str
    mode: str = "session"
    keyword: Optional[str] = None


def _get_context(mode: str, keyword, rows, meta):
    """Bangun context LLM sesuai mode. Historical = agregat DB (token-aman)."""
    if mode == "historical":
        from db_store import historical_context
        ctx = historical_context(keyword=keyword or None)
        if "Database kosong" in ctx:
            raise HTTPException(400, "Database historis masih kosong — scrape dulu atau backfill CSV.")
        return ctx, {"keyword": keyword or "semua (historis)", "mode": "historical"}
    if not rows:
        raise HTTPException(400, "rows kosong — jalankan scrape dulu atau pilih mode Historical.")
    import pandas as pd
    from core import build_sentiment_context
    return build_sentiment_context(pd.DataFrame(rows), meta or {}), meta or {}


@router.post("/ai/summary")
async def ai_summary(req: InsightRequest):
    from core import generate_executive_summary_from_context

    try:
        context, meta = _get_context(req.mode, req.keyword, req.rows, req.meta)
    except HTTPException:
        raise
    try:
        content = generate_executive_summary_from_context(context, meta)
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/ai/recommendations")
async def ai_recommendations(req: InsightRequest):
    from core import generate_recommendations_from_context

    try:
        context, meta = _get_context(req.mode, req.keyword, req.rows, req.meta)
    except HTTPException:
        raise
    try:
        content = generate_recommendations_from_context(context, meta)
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/ai/chat")
async def ai_chat(req: ChatRequest):
    from core import chat_completion_sync

    try:
        context, meta = _get_context(req.mode, req.keyword, req.rows, req.meta)
    except HTTPException:
        raise

    system_prompt = (
        "Kamu adalah Taspen Sentiment Analysis Agent. "
        "Jawab pertanyaan user tentang hasil sentiment berdasarkan context. "
        "Aturan: (1) jawab dari data, (2) jangan mengarang, (3) actionable, "
        "(4) Bahasa Indonesia natural.\n\n" + context
    )

    messages = [{"role": "system", "content": system_prompt}]
    # include last 10 history messages
    for m in req.messages[-10:]:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.user_input})

    try:
        content, reasoning = chat_completion_sync(messages, temperature=0.4, max_tokens=2000)
        return {"ok": True, "content": content, "reasoning": reasoning}
    except Exception as e:
        return {"ok": False, "error": str(e)}
