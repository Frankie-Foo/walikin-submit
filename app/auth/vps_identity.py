# -*- coding: utf-8 -*-
"""VPS identity stub — standalone deployment uses local auth only."""
from __future__ import annotations
from sqlmodel import Session


def fetch_vps_me_payload() -> dict | None:
    return None


def ensure_vps_user(session: Session, vps: dict):
    return None


def vps_display_name(vps: dict) -> str:
    return ""


def vps_username(vps: dict) -> str:
    return ""


def vps_profile(vps: dict) -> dict:
    return {}
