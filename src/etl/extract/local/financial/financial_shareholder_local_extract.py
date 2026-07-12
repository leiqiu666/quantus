"""前十大股东 本地 Extract：直接读库解析增量起点。"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.common.database import Database
from src.entities.data_entities.financial.financial_shareholder_top10_entities import Top10HoldersEntities


class ShareholderLocalExtract:
    def __init__(self) -> None:
        self._db = Database()

    def get_max_ann_date(self) -> str | None:
        session = self._db.get_session()
        try:
            result = (
                session.query(Top10HoldersEntities.ann_date)
                .filter(Top10HoldersEntities.ann_date != "")
                .order_by(Top10HoldersEntities.ann_date.desc())
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

        next_day = (
            datetime.strptime(max_ann, "%Y%m%d").date() + timedelta(days=1)
        ).strftime("%Y%m%d")

        if not configured:
            return next_day

        return max(configured, next_day)
