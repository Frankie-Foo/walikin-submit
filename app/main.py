# -*- coding: utf-8 -*-
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.router import router as auth_router
from app.auth.seed import seed_users
from app.config import get_settings
from app.database import bootstrap_database
from app.export.router import router as export_router
from app.logging_setup import setup_logging
from app.models.store_seed import seed_stores
from app.pages.router import router as pages_router
from app.walkin.router import router as walkin_router

PUBLIC_PATHS = {"/login", "/api/auth/login", "/api/auth/config", "/api/auth/vps-login",
                "/health", "/docs", "/openapi.json", "/redoc"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    bootstrap_database()
    seed_users()
    seed_stores()
    logger.info("Walikin-Submit started on {}:{}", settings.host, settings.port)
    yield
    logger.info("Walikin-Submit stopped")


app = FastAPI(title="Walikin Submit", version="1.0.0", lifespan=lifespan)

_CORS_ORIGINS = [
    "https://admin.vertu.cn",
    "https://pdca-workbench.vertu.cn",
    "http://localhost:8768",
    "http://127.0.0.1:8768",
]
app.add_middleware(CORSMiddleware, allow_origins=_CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def auth_redirect_middleware(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS:
        return await call_next(request)
    if path.startswith("/api/"):
        return await call_next(request)
    token = request.cookies.get("pdca_token")
    auth = request.headers.get("authorization", "")
    if not token and not auth.startswith("Bearer "):
        if not path.startswith("/login"):
            # Let through if VPS SSO params present — frontend JS handles the exchange
            if request.query_params.get("session_id") and request.query_params.get("user_id"):
                return await call_next(request)
            return RedirectResponse(f"/login?next={path}")
    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    if exc.status_code in (401, 403):
        return RedirectResponse(f"/login?next={request.url.path}")
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "Invalid request", "errors": exc.errors()}, status_code=422)


app.include_router(auth_router)
app.include_router(walkin_router)
app.include_router(export_router)
app.include_router(pages_router)
