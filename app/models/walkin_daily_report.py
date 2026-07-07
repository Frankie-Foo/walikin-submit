# -*- coding: utf-8 -*-
"""门店五件套日报表（每日进店来源 + 成交漏斗 + Sell-out）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class WalkinDailyReport(SQLModel, table=True):
    """经销商每日客流五件套数据。"""

    __tablename__ = "walkin_daily_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    report_date: str = Field(index=True, max_length=10)   # YYYY-MM-DD
    dealer_id: str = Field(index=True, max_length=64)     # 对应 walkin JSON 里的 store id
    dealer_name: str = Field(max_length=256)

    # 五件套来源人数（顺序对齐 Excel Summary 表头）
    walkin_visits: int = Field(default=0)         # Walk-ins 自然进店
    prospect_visits: int = Field(default=0)       # Prospects 潜在客户
    appointment_visits: int = Field(default=0)    # Appointments 预约进店
    online_visits: int = Field(default=0)         # Online 线上引流
    referral_visits: int = Field(default=0)       # Referral 介绍/转介绍
    sa_visits: int = Field(default=0)             # SA 主动开发

    # 转化漏斗
    touch_count: int = Field(default=0)           # 触摸产品（人次）
    use_count: int = Field(default=0)             # 试用体验（人次）
    wechat_add_count: int = Field(default=0)      # 微信添加数
    deal_count: int = Field(default=0)            # 成交组数
    deal_amount_yuan: float = Field(default=0.0)  # 成交金额（元，即 sell-out）

    notes: str = Field(default="", max_length=1024)
    submitted_by: str = Field(default="", max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def total_visits(self) -> int:
        return (
            self.walkin_visits
            + self.prospect_visits
            + self.appointment_visits
            + self.online_visits
            + self.referral_visits
            + self.sa_visits
        )
