# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Annotated
from urllib.parse import quote

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.auth.deps import require_role
from app.auth.models import User
from app.database import get_session
from app.models.dealer_store import DealerStore
from app.models.walkin_daily_report import WalkinDailyReport

router = APIRouter(prefix="/api/export", tags=["export"])


def _wb_response(wb: openpyxl.Workbook, filename: str) -> StreamingResponse:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    encoded = quote(filename.replace(" ", "_"), encoding="utf-8")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/walkin-metrics")
async def export_walkin_metrics(
    user: Annotated[User, Depends(require_role("dealer"))],
    session: Annotated[Session, Depends(get_session)],
    month: str = Query(""),
):
    stmt = select(WalkinDailyReport).order_by(WalkinDailyReport.report_date, WalkinDailyReport.dealer_id)
    if month and re.fullmatch(r"\d{4}-\d{2}", month):
        stmt = stmt.where(WalkinDailyReport.report_date.startswith(month))
    if user.role == "dealer":
        allowed = [user.dealer_id] if user.dealer_id else []
        if not allowed:
            raise HTTPException(status_code=403, detail="Account not bound to a store")
        stmt = stmt.where(WalkinDailyReport.dealer_id.in_(allowed))
    elif user.role == "sales":
        owned = session.exec(select(DealerStore.store_id).where(DealerStore.sales_owner == user.username)).all()
        stmt = stmt.where(WalkinDailyReport.dealer_id.in_(list(owned)))
    rows = session.exec(stmt).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"WalkIn_{month or 'All'}"
    headers = ["Date", "Store ID", "Store Name",
               "Appointments", "Prospects", "Online", "Referral", "SA", "Total Visitors",
               "Products Shown", "Products Used", "WeChat Added", "Deals",
               "Revenue", "Revenue (10k)", "Submitted By", "Submitted At"]
    ws.append(headers)
    for r in rows:
        total = r.appointment_visits + r.prospect_visits + r.online_visits + r.referral_visits + r.sa_visits
        ws.append([r.report_date, r.dealer_id, r.dealer_name,
                   r.appointment_visits, r.prospect_visits, r.online_visits,
                   r.referral_visits, r.sa_visits, total,
                   r.touch_count, r.use_count, r.wechat_add_count, r.deal_count,
                   r.deal_amount_yuan, round(r.deal_amount_yuan / 10000, 4),
                   r.submitted_by,
                   r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else ""])
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 32)

    fname = f"walkin_{month or 'all'}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return _wb_response(wb, fname)
