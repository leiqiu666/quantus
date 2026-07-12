"""指数成分权重大本地 Extract。"""

from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.index.index_weight_entities import IndexWeightEntities


class IndexWeightLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self) -> str | None:
        session = self._db.get_session()
        try:
            result = (
                session.query(IndexWeightEntities.trade_date)
                .order_by(IndexWeightEntities.trade_date.desc())
                .first()
            )
            return result[0] if result else None
        finally:
            session.close()

    def resolve_incremental_start_month(self, *, configured_start_month: str) -> str:
        """返回 YYYYMM 格式的增量起点月份。"""
        configured = (configured_start_month or "").strip()
        max_td = self.get_max_trade_date()

        if not max_td:
            return configured

        # 库内最大 trade_date 的月份 + 1
        from datetime import datetime
        max_ym = max_td[:6]
        y = int(max_ym[:4])
        m = int(max_ym[4:6]) + 1
        if m > 12:
            y += 1
            m = 1
        next_month = f"{y:04d}{m:02d}"

        if not configured:
            return next_month

        return max(configured, next_month)
