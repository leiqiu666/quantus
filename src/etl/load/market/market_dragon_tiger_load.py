"""龙虎榜 入库：top_list + top_inst 两张表。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.market.market_dragon_tiger_list_entities import TopListEntities
from src.entities.data_entities.market.market_dragon_tiger_inst_entities import TopInstEntities


class DragonTigerLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_top_list(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(TopListEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=TopListEntities,
            records=records,
            conflict_keys=["ts_code", "trade_date"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )

    def load_top_inst(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(TopInstEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=TopInstEntities,
            records=records,
            conflict_keys=["ts_code", "trade_date", "exalter", "side"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
        )
