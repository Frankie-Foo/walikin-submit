# -*- coding: utf-8 -*-
from __future__ import annotations

from loguru import logger
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_engine = None
_db_mode: str = "unknown"


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        connect_args = {"connect_timeout": 3} if url.startswith("postgresql") else {"check_same_thread": False}
        _engine = create_engine(url, echo=False, connect_args=connect_args,
                                pool_pre_ping=True, pool_size=5, max_overflow=10, pool_timeout=5)
    return _engine


def get_db_mode() -> str:
    return _db_mode


def _sqlite_fallback_url() -> str:
    return f"sqlite:///{(get_settings().data_dir / 'walkin_local.sqlite').as_posix()}"


def _probe_url(url: str) -> bool:
    args = {"connect_timeout": 3} if url.startswith("postgresql") else {"check_same_thread": False}
    try:
        probe = create_engine(url, connect_args=args, pool_pre_ping=True)
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe.dispose()
        return True
    except Exception as exc:
        logger.debug("DB probe failed {}: {}", url.split("@")[-1], exc)
        return False


def bootstrap_database() -> str:
    global _engine, _db_mode
    settings = get_settings()
    primary = settings.database_url

    if primary.startswith("sqlite"):
        _engine = None
        _db_mode = "sqlite"
        init_db()
        return _db_mode

    if _probe_url(primary):
        _engine = None
        _db_mode = "postgresql"
        init_db()
        logger.info("Connected to PostgreSQL")
        return _db_mode

    fallback = _sqlite_fallback_url()
    logger.warning("PostgreSQL unavailable, falling back to SQLite")
    _engine = None
    _db_mode = "sqlite-fallback"
    init_db()
    return _db_mode


def init_db() -> None:
    from app.auth.models import User  # noqa: F401
    from app.models.walkin_daily_report import WalkinDailyReport  # noqa: F401
    from app.models.dealer_store import DealerStore  # noqa: F401
    from app.models.audit_log import AuditLog  # noqa: F401

    SQLModel.metadata.create_all(get_engine())
    _migrate_schema()
    logger.info("DB tables ready")


def _migrate_schema() -> None:
    engine = get_engine()
    dialect = engine.dialect.name
    patches_pg = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS pwd_version INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS dealer_id VARCHAR(64) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS sales_name VARCHAR(128) DEFAULT ''",
        "ALTER TABLE dealer_stores ADD COLUMN IF NOT EXISTS dealer_level VARCHAR(8) DEFAULT 'L1'",
        "ALTER TABLE dealer_stores ADD COLUMN IF NOT EXISTS sales_owner VARCHAR(64) DEFAULT ''",
        "ALTER TABLE walkin_daily_reports ADD COLUMN IF NOT EXISTS walkin_visits INTEGER DEFAULT 0",
    ]
    patches_sqlite = [
        "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 1",
        "ALTER TABLE users ADD COLUMN pwd_version INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN dealer_id VARCHAR(64) DEFAULT ''",
        "ALTER TABLE users ADD COLUMN sales_name VARCHAR(128) DEFAULT ''",
        "ALTER TABLE dealer_stores ADD COLUMN dealer_level VARCHAR(8) DEFAULT 'L1'",
        "ALTER TABLE dealer_stores ADD COLUMN sales_owner VARCHAR(64) DEFAULT ''",
        "ALTER TABLE walkin_daily_reports ADD COLUMN walkin_visits INTEGER DEFAULT 0",
    ]
    with engine.connect() as conn:
        for sql in (patches_pg if dialect == "postgresql" else patches_sqlite):
            try:
                conn.exec_driver_sql(sql)
            except Exception:
                pass
        conn.commit()


def get_session():
    with Session(get_engine()) as session:
        yield session
