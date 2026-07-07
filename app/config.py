# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(APP_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        self.app_root = APP_ROOT
        self.host = os.environ.get("WALKIN_HOST", "0.0.0.0")
        self.port = int(os.environ.get("WALKIN_PORT", "8768"))
        self.secret_key = os.environ.get(
            "WALKIN_SECRET_KEY",
            "walkin-dev-secret-change-in-production",
        )
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(
            os.environ.get("WALKIN_TOKEN_EXPIRE_MINUTES", "480"),
        )
        self.database_url = self._resolve_database_url()
        self.data_dir = APP_ROOT / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = os.environ.get("WALKIN_LOG_LEVEL", "INFO")
        self.secure_cookies = os.environ.get("WALKIN_SECURE_COOKIES", "0") == "1"
        self.auth_mode = os.environ.get("WALKIN_AUTH_MODE", "local").strip().lower()
        self.odoo_base_url = os.environ.get("ODOO_BASE_URL", "").strip().rstrip("/")

    def _resolve_database_url(self) -> str:
        url = os.environ.get("WALKIN_DATABASE_URL", "").strip()
        if url:
            if url.startswith("postgresql://") and "+psycopg2" not in url:
                return url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url
        return "postgresql+psycopg2://pdca:pdca@localhost:5432/pdca"

    @property
    def frontend_dir(self) -> Path:
        return APP_ROOT / "frontend"


@lru_cache
def get_settings() -> Settings:
    return Settings()
