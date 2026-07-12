"""财务审计意见 Workflow。"""

from src.etl.extract.financial.financial_audit_extract import AuditExtract
from src.etl.load.financial.financial_audit_load import AuditLoad


class AuditWorkflow:
    def __init__(self):
        self.extract = AuditExtract()
        self.load = AuditLoad()

    def pull_fina_audit_by_period(self, ts_code: str, period: str) -> int:
        df = self.extract.pull_fina_audit_by_period(ts_code, period)
        return self.load.load_fina_audit(df)
