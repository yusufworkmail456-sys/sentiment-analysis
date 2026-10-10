"""API route for on-demand single-text sentiment analysis (Live Analyzer)."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["sentiment"])


class AnalyzeRequest(BaseModel):
    text: str


@router.post("/analyze")
async def analyze_text(req: AnalyzeRequest):
    """Classify a single text and return label + score."""
    from core import load_model, LABEL_ID
    from categorize import classify_text

    if not req.text.strip():
        return {"label": "", "score": 0.0, "kategori": ""}

    clf = load_model()
    res = clf([req.text[:512]])[0]
    label = LABEL_ID.get(res["label"].lower(), res["label"])
    score = round(res["score"], 4)
    kategori, _ = classify_text(req.text)

    return {"label": label, "score": score, "kategori": kategori}
