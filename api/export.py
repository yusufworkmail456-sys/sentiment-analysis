"""API route for PDF export."""
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["export"])


class ExportRequest(BaseModel):
    rows: list
    meta: dict
    ai_summary: Optional[str] = None
    ai_reco: Optional[str] = None


@router.post("/export/pdf")
async def export_pdf(req: ExportRequest):
    import pandas as pd
    from core import export_pdf as _export_pdf

    if not req.rows:
        return Response(content=b"", status_code=400)

    df = pd.DataFrame(req.rows)
    pdf_bytes = _export_pdf(df, req.meta, req.ai_summary, req.ai_reco)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=sentiment_report.pdf"},
    )
