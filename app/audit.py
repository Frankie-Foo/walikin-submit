# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from loguru import logger
from sqlmodel import Session
from app.database import get_engine
from app.models.audit_log import AuditLog


def log_action(username: str, action: str, resource: str = "", detail: dict | str = "", ip: str = "") -> None:
    try:
        detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail)
        with Session(get_engine()) as session:
            session.add(AuditLog(username=username, action=action, resource=resource,
                                 detail=detail_str[:2048], ip=ip or ""))
            session.commit()
    except Exception as exc:
        logger.debug("Audit log failed (non-fatal): {}", exc)
