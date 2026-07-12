"""trade_cal 表查询。"""

from __future__ import annotations

from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.stock.stock_trade_calendar_entities import TradeCalEntities


class TradeCalModel:
    def __init__(self) -> None:
        self.db = Database()
        self.db.ensure_table(TradeCalEntities)

    def get_min_cal_date(self, exchange: str) -> str | None:
        ex = (exchange or "").strip().upper()
        if not ex:
            return None
        session: Session = self.db.get_session()
        try:
            row = (
                session.query(func.min(TradeCalEntities.cal_date))
                .filter(TradeCalEntities.exchange == ex)
                .scalar()
            )
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()

    def get_max_cal_date(self, exchange: str) -> str | None:
        ex = (exchange or "").strip().upper()
        if not ex:
            return None
        session: Session = self.db.get_session()
        try:
            row = (
                session.query(func.max(TradeCalEntities.cal_date))
                .filter(TradeCalEntities.exchange == ex)
                .scalar()
            )
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()

    def get_open_trade_dates(
        self,
        *,
        start_date: str,
        end_date: str,
        exchange: str = "SSE",
    ) -> List[str]:
        ex = (exchange or "SSE").strip().upper()
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not start or not end or start > end:
            return []

        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(TradeCalEntities.cal_date)
                .filter(
                    TradeCalEntities.exchange == ex,
                    TradeCalEntities.is_open == "1",
                    TradeCalEntities.cal_date >= start,
                    TradeCalEntities.cal_date <= end,
                )
                .order_by(TradeCalEntities.cal_date.asc())
                .all()
            )
            return [str(r[0]).strip()[:8] for r in rows if r[0]]
        finally:
            session.close()

    def get_nearest_open_trade_date_on_or_before(
        self,
        date_key: str,
        *,
        exchange: str = "SSE",
    ) -> str | None:
        """返回 <= date_key 的最近 SSE 开市日；date_key 本身为开市日时返回自身。"""
        ex = (exchange or "SSE").strip().upper()
        dk = (date_key or "").strip()
        if not dk:
            return None
        session: Session = self.db.get_session()
        try:
            row = (
                session.query(func.max(TradeCalEntities.cal_date))
                .filter(
                    TradeCalEntities.exchange == ex,
                    TradeCalEntities.is_open == "1",
                    TradeCalEntities.cal_date <= dk,
                )
                .scalar()
            )
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()
