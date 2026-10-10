"""API route: info model yang dipakai (sentiment + LLM)."""
from fastapi import APIRouter

router = APIRouter(tags=["sessions"])


@router.get("/model/info")
async def model_info():
    import config
    from core import MODEL_NAME

    def short(m: str) -> str:
        """Tampilkan bagian nama model yang bermakna."""
        m = (m or "").strip()
        if not m:
            return "-"
        # provider/model → model ; org/model → bagian akhir yang pendek
        tail = m.split("/")[-1]
        return tail if len(tail) <= 28 else tail[:25] + "…"

    return {
        "ok": True,
        "sentiment_model": short(MODEL_NAME),
        "sentiment_full": MODEL_NAME,
        "llm_model": short(config.LLM_MODEL),
        "llm_full": config.LLM_MODEL,
    }
