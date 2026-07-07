# -*- coding: utf-8 -*-
"""用户与角色模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """本地多角色用户。"""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    hashed_password: str = Field(max_length=256)
    role: str = Field(default="viewer", max_length=32)
    display_name: str = Field(default="", max_length=128)
    sales_name: str = Field(default="", max_length=128, description="对应物流 CSV 中的 salesperson")
    dealer_id: str = Field(default="", max_length=64, description="dealer角色绑定的门店store_id")
    is_active: bool = Field(default=True)
    must_change_password: bool = Field(default=True)
    pwd_version: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


ROLE_LEVELS = {
    "viewer": 0,   # 只读访客
    "dealer": 1,   # 经销商员工：只能提交/查看自己门店数据
    "sales":  2,   # 内部销售：管理自己名下所有经销商
    "manager": 3,  # 主管：查看所有数据
    "admin":  4,   # 管理员：全部权限
}

DEFAULT_USERS = [
    ("admin", "admin123", "admin", "系统管理员", ""),
    ("manager", "manager123", "manager", "海外中台主管", ""),
    ("sales", "sales123", "sales", "何海文", "何海文"),
    ("viewer", "viewer123", "viewer", "只读访客", ""),
]
