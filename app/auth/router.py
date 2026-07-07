# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from collections import defaultdict
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.deps import get_current_user
from app.auth.models import User
from app.auth.security import create_access_token, hash_password, verify_password
from app.audit import log_action
from app.config import get_settings
from app.database import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

_FAIL_WINDOW = 300
_MAX_FAILS = 5
_LOCKOUT_SEC = 900
_fail_log: dict[str, list[float]] = defaultdict(list)


def _rate_limit_key(request: Request, username: str) -> str:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    return f"{ip}:{username}"


def _check_rate_limit(key: str) -> None:
    now = time.time()
    _fail_log[key] = [t for t in _fail_log[key] if now - t < _FAIL_WINDOW]
    if len(_fail_log[key]) >= _MAX_FAILS:
        wait = int(_LOCKOUT_SEC - (now - _fail_log[key][0]))
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Too many failures, retry in {max(wait//60,1)} min")


def _record_fail(key: str) -> None:
    _fail_log[key].append(time.time())


def _clear_fail(key: str) -> None:
    _fail_log.pop(key, None)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    role: str
    display_name: str
    sales_name: str = ""
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("/config")
async def auth_config():
    settings = get_settings()
    return {"auth_mode": settings.auth_mode}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response,
                session: Annotated[Session, Depends(get_session)]):
    settings = get_settings()
    key = _rate_limit_key(request, body.username)
    _check_rate_limit(key)
    user = session.exec(select(User).where(User.username == body.username)).first()
    if not user or not verify_password(body.password, user.hashed_password):
        _record_fail(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    _clear_fail(key)
    log_action(user.username, "login", ip=request.client.host if request.client else "")
    pwd_v = getattr(user, "pwd_version", 0) or 0
    token = create_access_token({"sub": user.username, "role": user.role, "pwd_v": pwd_v},
                                timedelta(minutes=settings.access_token_expire_minutes))
    response.set_cookie(key="pdca_token", value=token, httponly=True,
                        secure=settings.secure_cookies, samesite="lax",
                        max_age=settings.access_token_expire_minutes * 60)
    must_change = getattr(user, "must_change_password", False)
    return {"access_token": token, "token_type": "bearer", "must_change_password": must_change,
            "user": UserOut(username=user.username, role=user.role, display_name=user.display_name,
                            sales_name=getattr(user, "sales_name", "") or "",
                            must_change_password=must_change)}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("pdca_token")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[User, Depends(get_current_user)]):
    return UserOut(username=user.username, role=user.role, display_name=user.display_name,
                   sales_name=getattr(user, "sales_name", "") or "",
                   must_change_password=getattr(user, "must_change_password", False))


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request, response: Response,
                          user: Annotated[User, Depends(get_current_user)],
                          session: Annotated[Session, Depends(get_session)]):
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Wrong current password")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from old")
    user.hashed_password = hash_password(body.new_password)
    user.pwd_version = (getattr(user, "pwd_version", 0) or 0) + 1
    user.must_change_password = False
    session.add(user)
    session.commit()
    session.refresh(user)
    settings = get_settings()
    new_token = create_access_token({"sub": user.username, "role": user.role, "pwd_v": user.pwd_version},
                                    timedelta(minutes=settings.access_token_expire_minutes))
    response.set_cookie(key="pdca_token", value=new_token, httponly=True,
                        secure=settings.secure_cookies, samesite="lax",
                        max_age=settings.access_token_expire_minutes * 60)
    log_action(user.username, "change_password", ip=request.client.host if request.client else "")
    return {"ok": True, "access_token": new_token}
