"""沪深股通十大成交股本地 Extract。"""

from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.market.market_northbound_top10_entities import HsgtTop10Entities


class HsgtLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self) -> str | None:
        session = self._db.get_session()
        try:
            result = (
                session.query(HsgtTop10Entities.trade_date)
                .order_by(HsgtTop10Entities.trade_date.desc())
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
