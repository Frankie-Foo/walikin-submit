# -*- coding: utf-8 -*-
"""初始化默认用户。"""
from __future__ import annotations

from sqlmodel import Session, select

from app.auth.models import DEFAULT_USERS, User
from app.auth.security import hash_password
from app.database import get_engine, init_db
from loguru import logger


def seed_users() -> None:
    """首次启动写入默认多角色账号（已存在的不覆盖密码）。"""
    init_db()
    with Session(get_engine()) as session:
        for username, password, role, display_name, sales_name in DEFAULT_USERS:
            exists = session.exec(select(User).where(User.username == username)).first()
            if exists:
                changed = False
                if sales_name and not getattr(exists, "sales_name", ""):
                    exists.sales_name = sales_name
                    changed = True
                if display_name and not exists.display_name:
                    exists.display_name = display_name
                    changed = True
                if changed:
                    session.add(exists)
                continue
            session.add(
                User(
                    username=username,
                    hashed_password=hash_password(password),
                    role=role,
                    display_name=display_name,
                    sales_name=sales_name,
                    must_change_password=True,   # 首次登录必须改密
                    pwd_version=0,
                ),
            )
            logger.info("创建默认用户: {} ({})", username, role)
        session.commit()
