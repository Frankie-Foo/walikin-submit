# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.auth.deps import get_current_user
from app.config import get_settings

router = APIRouter(tags=["pages"])


@router.get("/")
async def home():
    return RedirectResponse("/walkin-submit")


@router.get("/login")
async def login_page():
    settings = get_settings()
    login = settings.frontend_dir / "login.html"
    if login.is_file():
        return FileResponse(login, media_type="text/html; charset=utf-8")
    return HTMLResponse("<p>login.html missing</p>")


@router.get("/walkin-submit")
@router.get("/walkin-submit/")
async def walkin_submit_page():
    settings = get_settings()
    html_path = settings.frontend_dir / "walkin_submit.html"
    if not html_path.is_file():
        raise HTTPException(status_code=404, detail="walkin_submit.html missing")
    return FileResponse(html_path, media_type="text/html; charset=utf-8")


@router.get("/health")
async def health():
    from app.database import get_db_mode
    mode = get_db_mode()
    return {"status": "ok", "service": "walikin-submit", "database": mode}
