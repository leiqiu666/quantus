"""财务审计意见 Load。"""

from src.common.database import Database
from src.entities.data_entities.financial.financial_audit_entities import FinaAuditEntities
from src.common.function import dataframe_to_list
import pandas as pd


class AuditLoad:
    def __init__(self):
        self.db = Database()

    def load_fina_audit(self, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0
        self.db.ensure_table(FinaAuditEntities)
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=FinaAuditEntities,
            records=records,
            conflict_keys=["ts_code", "end_date"],
            fallback_on_error=True,
            skip_length_check=True,
        )
