"""主营业务构成 Load。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database
from src.common.function import dataframe_to_list
from src.entities.data_entities.financial.financial_fina_mainbz_entities import FinaMainbzEntities


class FinaMainbzLoad:
    def __init__(self) -> None:
        self.db = Database()

    def load_fina_mainbz(self, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(FinaMainbzEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=FinaMainbzEntities,
            records=records,
            conflict_keys=["ts_code", "end_date", "bz_item", "bz_code"],
            fallback_on_error=True,
            skip_length_check=True,
        )
