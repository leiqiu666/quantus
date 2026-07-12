"""沪深股通十大成交股 Load。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.market.market_northbound_top10_entities import HsgtTop10Entities


class HsgtLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_hsgt_top10(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(HsgtTop10Entities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=HsgtTop10Entities,
            records=records,
            conflict_keys=["ts_code", "trade_date", "market_type"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
