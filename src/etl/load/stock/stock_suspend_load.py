"""停复牌 Load：upsert 到 PostgreSQL stock_suspend。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.stock.stock_suspend_entities import SuspendEntities


class SuspendLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_suspend(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(SuspendEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=SuspendEntities,
            records=records,
            conflict_keys=["ts_code", "trade_date", "suspend_type", "suspend_timing"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
