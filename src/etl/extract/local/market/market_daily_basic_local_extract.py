"""每日基本面指标本地 Extract：读库解析增量起点。"""

from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.market.market_daily_basic_entities import DailyBasicEntities


class DailyBasicLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self) -> str | None:
        """获取库内最大 trade_date。"""
        session = self._db.get_session()
        try:
            result = (
                session.query(DailyBasicEntities.trade_date)
                .order_by(DailyBasicEntities.trade_date.desc())
                .first()
            )
            return result[0] if result else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        """
        解析增量起点：max(configured_start, 库内 max(trade_date)+1)。

        库内无数据或 configured_start 更大时返回 configured_start。
        """
        configured = (configured_start or "").strip()
        max_td = self.get_max_trade_date()

        if not max_td:
            return configured

        # 库内最大日期的下一天
        from datetime import datetime, timedelta
        max_date = datetime.strptime(max_td, "%Y%m%d").date()
        next_day = (max_date + timedelta(days=1)).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)
