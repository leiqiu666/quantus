"""前十大股东 Load：upsert 到 PostgreSQL。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.financial.financial_shareholder_top10_entities import Top10HoldersEntities


class ShareholderLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_top10_holders(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(Top10HoldersEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=Top10HoldersEntities,
            records=records,
            conflict_keys=["ts_code", "end_date", "holder_name"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
