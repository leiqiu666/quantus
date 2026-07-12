"""分红送股本地 Extract：读库解析增量起点。"""

from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.market.market_dividend_entities import DividendEntities


class DividendLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_record_date(self) -> str | None:
        """获取库内最大 record_date。"""
        session = self._db.get_session()
        try:
            result = (
                session.query(DividendEntities.record_date)
                .filter(DividendEntities.record_date != "")
                .order_by(DividendEntities.record_date.desc())
                .first()
            )
            return result[0] if result else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        """
        解析增量起点：max(configured_start, 库内 max(record_date)+1)。
        """
        configured = (configured_start or "").strip()
        max_rd = self.get_max_record_date()

        if not max_rd:
            return configured

        from datetime import datetime, timedelta
        max_date = datetime.strptime(max_rd, "%Y%m%d").date()
        next_day = (max_date + timedelta(days=1)).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)
