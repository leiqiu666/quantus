"""停复牌本地 Extract：读库查询停牌日期。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.stock.stock_suspend_entities import SuspendEntities


class SuspendLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_trade_date(self) -> str | None:
        session: Session = self._db.get_session()
        try:
            row = session.query(func.max(SuspendEntities.trade_date)).scalar()
            if row is None:
                return None
            s = str(row).strip()
            return s[:8] if len(s) >= 8 else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        configured = (configured_start or "").strip()
        max_td = self.get_max_trade_date()

        if not max_td:
            return configured

        next_day = (
            datetime.strptime(max_td, "%Y%m%d").date() + timedelta(days=1)
        ).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)

    def preload_full_day_suspend_dates(
        self,
        *,
        ts_codes: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, set[str]]:
        """
        预加载全天停牌日期集合（suspend_type='S' AND suspend_timing=''）。

        返回：{ts_code: {trade_date, ...}}
        """
        session = self._db.get_session()
        try:
            query = (
                session.query(SuspendEntities.ts_code, SuspendEntities.trade_date)
                .filter(SuspendEntities.suspend_type == "S")
                .filter(SuspendEntities.suspend_timing == "")
            )
            if ts_codes:
                query = query.filter(SuspendEntities.ts_code.in_(ts_codes))
            if start_date:
                query = query.filter(SuspendEntities.trade_date >= start_date)
            if end_date:
                query = query.filter(SuspendEntities.trade_date <= end_date)

            result: dict[str, set[str]] = defaultdict(set)
            for ts_code, trade_date in query.all():
                result[ts_code].add(trade_date)
            return dict(result)
        finally:
            session.close()
