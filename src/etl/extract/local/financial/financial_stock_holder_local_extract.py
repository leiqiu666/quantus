"""股东户数本地 Extract。"""

from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.financial.financial_stock_holder_entities import StkHoldernumberEntities


class StkHoldernumberLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_ann_date(self) -> str | None:
        session = self._db.get_session()
        try:
            result = (
                session.query(StkHoldernumberEntities.ann_date)
                .filter(StkHoldernumberEntities.ann_date != "")
                .order_by(StkHoldernumberEntities.ann_date.desc())
                .first()
            )
            return result[0] if result else None
        finally:
            session.close()

    def resolve_incremental_start(self, *, configured_start: str) -> str:
        configured = (configured_start or "").strip()
        max_ann = self.get_max_ann_date()

        if not max_ann:
            return configured

        from datetime import datetime, timedelta
        max_date = datetime.strptime(max_ann, "%Y%m%d").date()
        next_day = (max_date + timedelta(days=1)).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)
