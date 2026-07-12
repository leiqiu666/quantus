from typing import Type, Any
from typing import List
import pandas as pd

from src.common.database import Database
from src.common.function import dataframe_to_list
from src.entities.data_entities.stock.stock_list_entities import StockListEntities
class StockLoad:
    def __init__(self):
        self.db = Database()

    def load_stock(self, df: pd.DataFrame) -> int:
        """
        Args:
            df: 待入库的数据表（DataFrame）。
        Returns:
            实际写入/更新的记录数。
        """
        if df is None or df.empty:
            return 0
        
        records = dataframe_to_list(df)
        saved_count = self.db.bulk_upsert_postgresql(
            model_class=StockListEntities,
            records=records,
            conflict_keys=['ts_code'],
            fallback_on_error=True
        )
        return saved_count