# -*- coding: utf-8 -*-
"""门店/经销商主数据（动态维护，替代硬编码下拉列表）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class DealerStore(SQLModel, table=True):
    __tablename__ = "dealer_stores"

    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(max_length=256)
    region: str = Field(default="", max_length=64)      # 中东 / 欧洲 / 南亚 / 东南亚 / 中亚
    country: str = Field(default="", max_length=64)
    dealer_level: str = Field(default="L1", max_length=8)   # L1 / L2
    sales_owner: str = Field(default="", max_length=64, index=True)  # 负责该经销商的内部销售 username
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
