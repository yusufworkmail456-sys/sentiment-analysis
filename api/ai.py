"""API routes for AI insight: executive summary, recommendations, chatbot."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(tags=["ai"])


class InsightRequest(BaseModel):
    rows: list          # list of sentiment row dicts
    meta: dict


class ChatMessage(BaseModel):
    role: str           # user | assistant
    content: str


class ChatRequest(BaseModel):
    rows: list
    meta: dict
    messages: List[ChatMessage]
    user_input: str


@router.post("/ai/summary")
async def ai_summary(req: InsightRequest):
    import pandas as pd
    from core import generate_executive_summary

    if not req.rows:
        raise HTTPException(400, "rows kosong")
    df = pd.DataFrame(req.rows)
    try:
        content = generate_executive_summary(df, req.meta)
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/ai/recommendations")
async def ai_recommendations(req: InsightRequest):
    import pandas as pd
    from core import generate_recommendations

    if not req.rows:
        raise HTTPException(400, "rows kosong")
    df = pd.DataFrame(req.rows)
    try:
        content = generate_recommendations(df, req.meta)
        return {"ok": True, "content": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/ai/chat")
async def ai_chat(req: ChatRequest):
    import pandas as pd
    from core import build_sentiment_context, chat_completion_sync

    if not req.rows:
        raise HTTPException(400, "rows kosong")
    df = pd.DataFrame(req.rows)

    context = build_sentiment_context(df, req.meta)
    system_prompt = (
        "Kamu adalah Sentix AI Analysis Agent. "
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
