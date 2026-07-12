"""财报披露计划 Load。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database
from src.common.function import dataframe_to_list
from src.entities.data_entities.financial.financial_disclosure_date_entities import (
    DisclosureDateEntities,
)


class DisclosureDateLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_disclosure_date(self, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(DisclosureDateEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=DisclosureDateEntities,
            records=records,
            conflict_keys=["ts_code", "end_date"],
            fallback_on_error=True,
            skip_length_check=True,
        )
