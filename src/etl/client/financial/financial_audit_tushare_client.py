"""财务审计意见 Tushare Client（fina_audit）。"""

from src.common.tushare_client import TushareClient
from src.common.function import create_rate_limiter
from src.etl.client.base import call_with_network_retry
import pandas as pd

AUDIT_COLUMNS = [
    "ts_code", "ann_date", "end_date",
    "audit_result", "audit_fees", "audit_agency", "audit_sign",
]

_acquire_audit_rate_limit = create_rate_limiter(200)


def finalize_fina_audit(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "ann_date" in out.columns:
        out["ann_date"] = out["ann_date"].astype(str).str.strip()
    if "end_date" in out.columns:
        out["end_date"] = out["end_date"].astype(str).str.strip()
    if "audit_result" in out.columns:
        out["audit_result"] = out["audit_result"].astype(str).str.strip()

    return out


class TushareAuditClient:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_fina_audit_by_period(self, ts_code: str, period: str) -> pd.DataFrame:
        _acquire_audit_rate_limit()
        df = call_with_network_retry(
            self.ts.fina_audit,
            ts_code=ts_code,
            period=period,
            fields=",".join(AUDIT_COLUMNS),
        )
        return finalize_fina_audit(df)
