"""财务审计意见 Extract。"""

from src.etl.client.financial.financial_audit_tushare_client import TushareAuditClient
import pandas as pd


class AuditExtract:
    def __init__(self):
        self.tushare_client = TushareAuditClient()

    def pull_fina_audit_by_period(self, ts_code: str, period: str) -> pd.DataFrame:
        return self.tushare_client.pull_fina_audit_by_period(ts_code, period)
