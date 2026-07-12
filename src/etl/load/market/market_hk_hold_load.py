"""沪深港股通持股明细 Load：upsert 到 PostgreSQL。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.market.market_hk_hold_entities import HkHoldEntities


class HkHoldLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_hk_hold(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(HkHoldEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=HkHoldEntities,
            records=records,
            conflict_keys=["trade_date", "ts_code", "exchange"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
