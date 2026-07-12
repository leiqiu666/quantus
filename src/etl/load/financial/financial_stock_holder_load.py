"""股东户数 Load。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.financial.financial_stock_holder_entities import StkHoldernumberEntities


class StkHoldernumberLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_stk_holdernumber(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(StkHoldernumberEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=StkHoldernumberEntities,
            records=records,
            conflict_keys=["ts_code", "end_date"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
