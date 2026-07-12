"""指数日线本地 Extract。"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.common.database import Database
from src.entities.data_entities.index.index_daily_entities import IndexDailyEntities


class IndexDailyLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self, ts_code: str) -> str | None:
        ts_code = (ts_code or "").strip()
        if not ts_code:
            return None
        session = self._db.get_session()
        try:
            result = (
                session.query(IndexDailyEntities.trade_date)
                .filter(IndexDailyEntities.ts_code == ts_code)
                .order_by(IndexDailyEntities.trade_date.desc())
                .first()
            )
            return result[0] if result else None
        finally:
            session.close()

    def resolve_incremental_start_date(
        self,
        *,
        ts_code: str,
        configured_start_date: str,
    ) -> str:
        configured = (configured_start_date or "").strip()
        max_td = self.get_max_trade_date(ts_code)
        if not max_td:
            return configured
        dt = datetime.strptime(max_td, "%Y%m%d") + timedelta(days=1)
        next_date = dt.strftime("%Y%m%d")
        if not configured:
            return next_date
        return max(configured, next_date)
