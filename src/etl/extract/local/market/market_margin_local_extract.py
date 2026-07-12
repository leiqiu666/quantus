"""融资融券明细本地 Extract。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.market.market_margin_entities import MarginDetailEntities


class MarginLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_peak_daily_universe_count(self, *, end_date: str | None = None) -> int:
        """历史单日融资融券标的峰值（用作完整性分母）。"""
        session: Session = self._db.get_session()
        try:
            q = session.query(
                MarginDetailEntities.trade_date,
                func.count(func.distinct(MarginDetailEntities.ts_code)).label("cnt"),
            )
            if end_date:
                q = q.filter(MarginDetailEntities.trade_date <= end_date)
            rows = q.group_by(MarginDetailEntities.trade_date).all()
            if not rows:
                return 0
            return max(int(r[1]) for r in rows)
        finally:
            session.close()

    def get_max_trade_date(self) -> str | None:
        session = self._db.get_session()
        try:
            result = (
                session.query(MarginDetailEntities.trade_date)
                .order_by(MarginDetailEntities.trade_date.desc())
                .first()
            )
            return result[0] if result else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        configured = (configured_start or "").strip()
        max_td = self.get_max_trade_date()

        if not max_td:
            return configured

        from datetime import datetime, timedelta
        max_date = datetime.strptime(max_td, "%Y%m%d").date()
        next_day = (max_date + timedelta(days=1)).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)
