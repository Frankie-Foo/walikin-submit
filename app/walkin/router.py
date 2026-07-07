# -*- coding: utf-8 -*-
"""门店五件套录入 API。"""
from __future__ import annotations

import re
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.audit import log_action
from app.auth.deps import get_current_user, require_role
from app.auth.models import User
from app.database import get_session
from app.models.dealer_store import DealerStore
from app.models.walkin_daily_report import WalkinDailyReport

router = APIRouter(tags=["walkin"])


@router.get("/api/my-stores")
async def get_my_stores(
    user: Annotated[User, Depends(require_role("dealer"))],
    session: Annotated[Session, Depends(get_session)],
):
    stmt = select(DealerStore).where(DealerStore.is_active == True)
    if user.role == "dealer":
        stmt = stmt.where(DealerStore.store_id == (user.dealer_id or "__none__"))
    elif user.role == "sales":
        stmt = stmt.where(DealerStore.sales_owner == user.username)
    stores = session.exec(stmt.order_by(DealerStore.region, DealerStore.sort_order)).all()
    return [
        {"store_id": s.store_id, "name": s.name, "region": s.region,
         "country": s.country, "dealer_level": s.dealer_level, "sales_owner": s.sales_owner}
        for s in stores
    ]


class WalkinMetricsSubmit(BaseModel):
    report_date: str
    dealer_id: str
    dealer_name: str
    walkin_visits: int = 0
    prospect_visits: int = 0
    appointment_visits: int = 0
    online_visits: int = 0
    referral_visits: int = 0
    sa_visits: int = 0
    touch_count: int = 0
    use_count: int = 0
    wechat_add_count: int = 0
    deal_count: int = 0
    deal_amount_yuan: float = 0.0
    notes: str = ""


@router.post("/api/walkin-metrics")
async def submit_walkin_metrics(
    body: WalkinMetricsSubmit,
    user: Annotated[User, Depends(require_role("dealer"))],
    session: Annotated[Session, Depends(get_session)],
):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", body.report_date):
        raise HTTPException(status_code=422, detail="report_date must be YYYY-MM-DD")
    if not body.dealer_id.strip():
        raise HTTPException(status_code=422, detail="dealer_id required")
    if user.role == "dealer":
        if not user.dealer_id:
            raise HTTPException(status_code=403, detail="Account not bound to a store")
        if body.dealer_id != user.dealer_id:
            raise HTTPException(status_code=403, detail="Can only submit for your own store")

    existing = session.exec(
        select(WalkinDailyReport).where(
            WalkinDailyReport.report_date == body.report_date,
            WalkinDailyReport.dealer_id == body.dealer_id,
        )
    ).first()

    data = dict(
        report_date=body.report_date, dealer_id=body.dealer_id, dealer_name=body.dealer_name,
        walkin_visits=max(0, body.walkin_visits), prospect_visits=max(0, body.prospect_visits),
        appointment_visits=max(0, body.appointment_visits), online_visits=max(0, body.online_visits),
        referral_visits=max(0, body.referral_visits), sa_visits=max(0, body.sa_visits),
        touch_count=max(0, body.touch_count), use_count=max(0, body.use_count),
        wechat_add_count=max(0, body.wechat_add_count), deal_count=max(0, body.deal_count),
        deal_amount_yuan=max(0.0, body.deal_amount_yuan), notes=body.notes,
        submitted_by=user.username,
    )
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        session.add(existing)
    else:
        session.add(WalkinDailyReport(**data))
    session.commit()
    log_action(user.username, "submit_five_kit",
               resource=f"{body.dealer_id}:{body.report_date}",
               detail={"dealer": body.dealer_name, "deal_yuan": body.deal_amount_yuan})
    return {"ok": True, "message": "Saved"}


def _allowed_dealer_ids(user: User, session) -> list[str] | None:
    if user.role == "dealer":
        return [user.dealer_id] if user.dealer_id else []
    if user.role == "sales":
        return list(session.exec(
            select(DealerStore.store_id).where(DealerStore.sales_owner == user.username)
        ).all())
    return None


@router.get("/api/walkin-metrics")
async def list_walkin_metrics(
    user: Annotated[User, Depends(require_role("dealer"))],
    session: Annotated[Session, Depends(get_session)],
    month: str = Query(""),
    dealer_id: str = Query(""),
):
    stmt = select(WalkinDailyReport)
    if month and re.fullmatch(r"\d{4}-\d{2}", month):
        stmt = stmt.where(WalkinDailyReport.report_date.startswith(month))
    allowed = _allowed_dealer_ids(user, session)
    if allowed is not None:
        if not allowed:
            return {"count": 0, "items": []}
        stmt = stmt.where(WalkinDailyReport.dealer_id.in_(allowed))
    if dealer_id and (allowed is None or dealer_id in allowed):
        stmt = stmt.where(WalkinDailyReport.dealer_id == dealer_id)
    rows = session.exec(stmt.order_by(WalkinDailyReport.report_date.desc())).all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id, "report_date": r.report_date,
                "dealer_id": r.dealer_id, "dealer_name": r.dealer_name,
                "five_kit": {"walkin": r.walkin_visits, "prospect": r.prospect_visits,
                             "appointment": r.appointment_visits, "online": r.online_visits,
                             "referral": r.referral_visits, "sa": r.sa_visits, "total": r.total_visits},
                "funnel": {"total_visits": r.total_visits, "touch_count": r.touch_count,
                           "use_count": r.use_count, "wechat_add_count": r.wechat_add_count,
                           "deal_count": r.deal_count, "deal_amount_yuan": r.deal_amount_yuan},
                "notes": r.notes, "submitted_by": r.submitted_by,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ],
    }
