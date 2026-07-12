"""业绩快报 Load。"""

from src.common.database import Database
from src.entities.data_entities.financial.financial_express_entities import ExpressEntities
from src.common.function import dataframe_to_list
import pandas as pd


class ExpressLoad:
    def __init__(self):
        self.db = Database()

    def load_express(self, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(ExpressEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=ExpressEntities,
            records=records,
            conflict_keys=["ts_code", "end_date"],
            fallback_on_error=True,
            skip_length_check=True,
        )
