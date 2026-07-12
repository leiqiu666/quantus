"""大宗交易 本地 Extract：直接读库解析增量起点。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.market.market_block_trade_entities import BlockTradeEntities


class BlockTradeLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self) -> str | None:
        session: Session = self._db.get_session()
        try:
            row = session.query(func.max(BlockTradeEntities.trade_date)).scalar()
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
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
