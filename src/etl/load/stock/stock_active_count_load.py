from __future__ import annotations

from src.common.database import Database
from src.entities.data_entities.stock.stock_active_count_entities import (
    StockActiveCountEntities,
)


class StockActiveCountLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_active_count_rows(self, records: list[dict]) -> int:
        if not records:
            return 0
        self.db.ensure_table(StockActiveCountEntities)
        return self.db.bulk_upsert_postgresql(
            model_class=StockActiveCountEntities,
            records=records,
            conflict_keys=["date_key"],
            fallback_on_error=True,
        )
