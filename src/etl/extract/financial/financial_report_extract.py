"""财报 Extract：编排数据源 Client（当前仅 Tushare）。"""

import pandas as pd

from src.etl.client.financial.financial_report_tushare_client import TushareReportClient


class ReportExtract:
    def __init__(self) -> None:
        self._client = TushareReportClient()

    def pull(self, report_type: str, **kwargs) -> pd.DataFrame:
        """按报告期 VIP 拉取（income/balance/cashflow）。"""
        return self._client.pull(report_type, **kwargs)

    def pull_by_code(self, report_type: str, ts_code: str, **kwargs) -> pd.DataFrame:
        """按 ts_code+end_date 普通接口拉取。"""
        return self._client.pull_by_code(report_type, ts_code, **kwargs)
