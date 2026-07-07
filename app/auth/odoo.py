# -*- coding: utf-8 -*-
"""Odoo session verification for VPS SSO."""
from __future__ import annotations

import requests
from loguru import logger


def verify_odoo_session(odoo_base_url: str, session_id: str, user_id: int) -> dict | None:
    """
    Verify Odoo session and return employee info.
    Returns None if session is invalid or uid mismatch.
    """
    try:
        resp = requests.post(
            f"{odoo_base_url.rstrip('/')}/web/session/get_session_info",
            json={"jsonrpc": "2.0", "method": "call", "params": {}, "id": 1},
            cookies={"session_id": session_id},
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Odoo session check failed: {}", exc)
        return None

    result = data.get("result") or {}
    uid = result.get("uid")

    if not uid or int(uid) != int(user_id):
        logger.warning("Odoo uid mismatch: got={} expected={}", uid, user_id)
        return None

    return {
        "uid": int(uid),
        "name": result.get("name") or result.get("display_name") or f"vps_{user_id}",
        "login": result.get("login") or f"vps_{user_id}",
        "partner_display_name": result.get("partner_display_name") or "",
    }


def fetch_odoo_employee(odoo_base_url: str, session_id: str, user_id: int) -> dict:
    """Fetch barcode and department from hr_employee via JSON-RPC."""
    try:
        resp = requests.post(
            f"{odoo_base_url.rstrip('/')}/web/dataset/call_kw",
            json={
                "jsonrpc": "2.0", "method": "call", "id": 2,
                "params": {
                    "model": "hr.employee",
                    "method": "search_read",
                    "args": [[["user_id", "=", user_id]]],
                    "kwargs": {"fields": ["name", "barcode", "department_id", "job_title"], "limit": 1},
                },
            },
            cookies={"session_id": session_id},
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        result = resp.json().get("result") or []
        if result:
            emp = result[0]
            dept = emp.get("department_id")
            return {
                "name": emp.get("name", ""),
                "barcode": emp.get("barcode") or "",
                "department": dept[1] if isinstance(dept, list) else "",
                "job_title": emp.get("job_title") or "",
            }
    except Exception as exc:
        logger.debug("Odoo employee fetch failed (non-fatal): {}", exc)
    return {}
