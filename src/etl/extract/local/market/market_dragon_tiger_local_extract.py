"""龙虎榜 本地 Extract：直接读库解析增量起点。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.market.market_dragon_tiger_list_entities import TopListEntities
from src.entities.data_entities.market.market_dragon_tiger_inst_entities import TopInstEntities


class DragonTigerLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self) -> str | None:
        """库内最大 trade_date（取 top_list 和 top_inst 中较大者）。"""
        session: Session = self._db.get_session()
        try:
            list_max = session.query(func.max(TopListEntities.trade_date)).scalar()
            inst_max = session.query(func.max(TopInstEntities.trade_date)).scalar()
            candidates = [
                str(v).strip()[:8]
                for v in (list_max, inst_max)
                if v is not None and str(v).strip()
            ]
            return max(candidates) if candidates else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        from datetime import datetime, timedelta

        configured = (configured_start or "").strip()
        max_td = self.get_max_trade_date()

        if not max_td:
            return configured

        max_date = datetime.strptime(max_td, "%Y%m%d").date()
        next_day = (max_date + timedelta(days=1)).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)
