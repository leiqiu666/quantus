"""completeness_snapshot 读模型。"""

from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.completeness_snapshot_entities import (
    CompletenessSnapshotEntities,
)


class CompletenessSnapshotModel:
    def __init__(self) -> None:
        self._db = Database()

    def list_by_sources_and_range(
        self,
        source_names: list[str],
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict]:
        if not source_names:
            return []
        session = self._db.get_session()
        try:
            q = session.query(CompletenessSnapshotEntities).filter(
                CompletenessSnapshotEntities.source_name.in_(source_names)
            )
            if start:
                q = q.filter(CompletenessSnapshotEntities.date_key >= start)
            if end:
                q = q.filter(CompletenessSnapshotEntities.date_key <= end)
            rows = q.order_by(CompletenessSnapshotEntities.date_key).all()
            return [
                {
                    "source_name": r.source_name,
                    "date_key": r.date_key,
                    "period_stock_count": int(r.period_stock_count or 0),
                    "resolved_count": int(r.resolved_count or 0),
                }
                for r in rows
            ]
        finally:
            session.close()

    def count_distinct_date_keys(
        self,
        source_names: list[str],
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> int:
        rows = self.list_by_sources_and_range(source_names, start=start, end=end)
        return len({r["date_key"] for r in rows})
