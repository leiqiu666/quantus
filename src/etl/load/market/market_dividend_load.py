"""分红送股 Load：upsert 到 PostgreSQL。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.market.market_dividend_entities import DividendEntities


class DividendLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_dividend(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(DividendEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=DividendEntities,
            records=records,
            conflict_keys=["ts_code", "end_date", "div_proc"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
