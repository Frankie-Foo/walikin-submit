# -*- coding: utf-8 -*-
"""真实经销商主数据初始化。"""
from __future__ import annotations

from loguru import logger
from sqlmodel import Session, select

from app.database import get_engine
from app.models.dealer_store import DealerStore

# (store_id, name, region, country, dealer_level, sales_owner)
_STORES: list[tuple[str, str, str, str, str, str]] = [
    # ── 中东 ──────────────────────────────────────────────────────────────────
    ("me001", "AI-SARAF CO",                              "中东", "伊拉克",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me002", "Behzadi Boutique",                         "中东", "伊拉克",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me003", "Billionaire Collections",                  "中东", "阿联酋",       "L2", "DEHDEHDAHOUMAIMA"),
    ("me004", "CLICK TECH SERVICES",                      "中东", "卡塔尔",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me005", "Dar Al Sabaek",                            "中东", "科威特",       "L1", "viki"),
    ("me006", "HASSIB ABDALLAH AMIR ALLAH",               "中东", "伊拉克",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me007", "Luxem Store",                              "中东", "伊朗",         "L1", "DEHDEHDAHOUMAIMA"),
    ("me008", "Mkateb for e-commerce",                    "中东", "约旦",         "L1", "DEHDEHDAHOUMAIMA"),
    ("me009", "My Shops Electronics Trading LLC",         "中东", "阿联酋",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me010", "Rashid Inkman Rashid",                     "中东", "伊拉克",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me011", "Safiran Hamrah",                           "中东", "伊朗",         "L1", "viki"),
    ("me012", "TIVALI Commercial Broker LLC",             "中东", "伊朗",         "L1", "DEHDEHDAHOUMAIMA"),
    ("me013", "Veysel Sevis Ltd",                         "中东", "土耳其",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me014", "Bestcom",                                  "中东", "乌克兰",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me015", "FRONTANA GIDA DIS TICARET LIMITED",        "中东", "乌克兰",       "L1", "DEHDEHDAHOUMAIMA"),
    ("me016", "IQ-QUEST SP. Z O.O.",                      "中东", "德国",         "L1", "DEHDEHDAHOUMAIMA"),
    # ── 欧洲 ──────────────────────────────────────────────────────────────────
    ("eu001", "Optimizers d.o.o.",                        "欧洲", "斯洛文尼亚",   "L1", "DEHDEHDAHOUMAIMA"),
    ("eu002", "Robo Trading Ltd",                         "欧洲", "保加利亚",     "L1", "DEHDEHDAHOUMAIMA"),
    ("eu003", "VERTU LONDON LTD",                         "欧洲", "英国",         "L2", "DEHDEHDAHOUMAIMA"),
    ("eu004", "vipconnect.de",                            "欧洲", "德国",         "L1", "DEHDEHDAHOUMAIMA"),
    ("eu005", "Quantum Reserve",                          "欧洲", "瑞士",         "L1", "viki"),
    # ── 南亚 ──────────────────────────────────────────────────────────────────
    ("sa001", "GURU ELECTRONICS SINGAPORE PTE LTD",       "南亚", "印度",         "L1", "april"),
    ("sa002", "LZB INDIA ELECTRIC PRIVATE LIMITED",       "南亚", "印度",         "L1", "april"),
    ("sa003", "Sidd Senthil",                             "南亚", "印度",         "L1", "haiwen"),
    ("sa004", "Parth Kamlesh Doshi",                      "南亚", "印度",         "L1", "helongcheng"),
    ("sa005", "Sun International General Trading",        "南亚", "印度",         "L1", "april"),
    # ── 东南亚 ────────────────────────────────────────────────────────────────
    ("sea01", "BIN BIN INVESTMENT(CAMBODIA) CO LTD",      "东南亚", "柬埔寨",     "L1", "yubing"),
    ("sea02a", "VMG Communication and Technology JSC · Saigon",    "东南亚", "越南", "L2", "yubing"),
    ("sea02b", "VMG Communication and Technology JSC · Caravelle", "东南亚", "越南", "L2", "yubing"),
    ("sea02c", "VMG Communication and Technology JSC · Majestic",  "东南亚", "越南", "L2", "yubing"),
    ("sea02d", "VMG Communication and Technology JSC · REX",       "东南亚", "越南", "L2", "yubing"),
    ("sea03", "VST ECS (Thailand) Co., Ltd.",             "东南亚", "泰国",       "L1", "yubing"),
    ("sea04", "Zmc automotive Pte Ltd",                   "东南亚", "新加坡",     "L1", "helongcheng"),
    # ── 中亚 ──────────────────────────────────────────────────────────────────
    ("ca001", "Altyn Zaman H.J.",                         "中亚", "土库曼斯坦",   "L1", "april"),
    ("ca002", "Bizcon Group",                             "中亚", "乌兹别克斯坦", "L1", "april"),
    ("ca003", "CONTINENTAL PLUS LLC.",                    "中亚", "俄罗斯",       "L1", "april"),
    ("ca004", "LLC TC Azimut",                            "中亚", "俄罗斯",       "L2", "april"),
    ("ca005", "LYZHINA OLGA",                             "中亚", "俄罗斯",       "L1", "april"),
    ("ca006", "reStore",                                  "中亚", "哈萨克斯坦",   "L1", "april"),
]

# 旧测试数据的 store_id 前缀，检测到则自动清除重建
_OLD_PREFIXES = ("d0", "d1", "d2", "d3", "vn")


def seed_stores() -> None:
    """初始化/重建门店主数据。如检测到旧测试数据则自动清除。"""
    with Session(get_engine()) as session:
        existing = session.exec(select(DealerStore)).all()

        if existing:
            is_old = all(
                any(s.store_id.startswith(p) for p in _OLD_PREFIXES)
                for s in existing
            )
            if is_old:
                logger.info("检测到旧测试门店数据 ({} 条)，清除并重建...", len(existing))
                for s in existing:
                    session.delete(s)
                session.commit()
                # 同步清除引用旧 store_id 的五件套记录
                try:
                    from app.models.walkin_daily_report import WalkinDailyReport
                    old_reports = session.exec(select(WalkinDailyReport)).all()
                    for r in old_reports:
                        session.delete(r)
                    session.commit()
                    logger.info("已清除旧五件套测试数据")
                except Exception as exc:
                    logger.debug("清除旧五件套记录跳过: {}", exc)
            else:
                # 已有真实数据，只做 upsert（补充缺失条目）
                existing_ids = {s.store_id for s in existing}
                added = 0
                for i, row in enumerate(_STORES):
                    sid = row[0]
                    if sid not in existing_ids:
                        session.add(DealerStore(
                            store_id=sid, name=row[1], region=row[2],
                            country=row[3], dealer_level=row[4],
                            sales_owner=row[5], sort_order=i,
                        ))
                        added += 1
                if added:
                    session.commit()
                    logger.info("门店主数据补充 {} 条", added)
                return

        for i, row in enumerate(_STORES):
            session.add(DealerStore(
                store_id=row[0], name=row[1], region=row[2],
                country=row[3], dealer_level=row[4],
                sales_owner=row[5], sort_order=i,
            ))
        session.commit()
        logger.info("门店主数据已初始化（真实经销商），共 {} 条", len(_STORES))
