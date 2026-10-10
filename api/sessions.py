"""API routes for credential/session management."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["sessions"])


class IGSessionRequest(BaseModel):
    session_id: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""


class FBSessionRequest(BaseModel):
    cookie: str


class TTSessionRequest(BaseModel):
    ms_token: str


@router.post("/sessions/instagram")
async def save_ig_session(req: IGSessionRequest):
    from scrapers_extra import save_session, check_session
    import os

    data = {}
    if req.session_id: data["session_id"] = req.session_id
    if req.username:   data["username"]   = req.username
    if req.password:   data["password"]   = req.password
    if not data:
        return {"ok": False, "error": "Isi minimal satu field"}

    # Remove old file to force re-login
    from pathlib import Path
    old = Path(__file__).parent.parent / "ig_session.json"
    if old.exists():
        old.unlink()

    if req.session_id: os.environ["IG_SESSIONID"] = req.session_id
    if req.username:   os.environ["IG_USER"]      = req.username
    if req.password:   os.environ["IG_PASS"]      = req.password

    save_session("instagram", data)
    return {"ok": True, "status": check_session("instagram")}


@router.post("/sessions/facebook")
async def save_fb_session(req: FBSessionRequest):
    from scrapers_extra import save_session, check_session, test_facebook

    ok, msg = test_facebook(req.cookie)
    if not ok:
        return {"ok": False, "error": msg}
    save_session("facebook", {"cookie": req.cookie})
    return {"ok": True, "status": check_session("facebook")}


@router.post("/sessions/tiktok")
async def save_tt_session(req: TTSessionRequest):
    from scrapers_extra import save_session, check_session, test_tiktok

    ok, msg = test_tiktok(req.ms_token)
    if not ok:
        return {"ok": False, "error": msg}
    save_session("tiktok", {"ms_token": req.ms_token})
    return {"ok": True, "status": check_session("tiktok")}


@router.get("/sessions/status")
async def sessions_status():
    from scrapers_extra import check_session

    return {
        "instagram": check_session("instagram"),
        "facebook":  check_session("facebook"),
        "tiktok":    check_session("tiktok"),
        "youtube":   "ok",
        "web":       "ok",
        "playstore": "ok",
    }
