# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from loguru import logger
from app.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    log_dir = settings.data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level,
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
    logger.add(log_dir / "walkin_{time:YYYY-MM-DD}.log",
               rotation="00:00", retention="30 days", encoding="utf-8", level=settings.log_level)
