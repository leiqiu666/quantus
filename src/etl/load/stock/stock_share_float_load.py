"""限售股解禁 Load：upsert 到 PostgreSQL。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.stock.stock_share_float_entities import StockShareFloatEntities


class StockShareFloatLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_share_float(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(StockShareFloatEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=StockShareFloatEntities,
            records=records,
            conflict_keys=["ts_code", "float_date", "holder_name", "share_type"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
