"""Tushare 财报 Client（income / balance / cashflow，参数化 dispatch）。"""

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.entities.client_entities.tushare_entities import tushare_entities
from src.etl.client.base import apply_source_column_map, call_with_network_retry


@dataclass(frozen=True)
class _TushareReportSpec:
    """Tushare 三表 endpoint 配置：VIP 按期 / 普通按代码 + 列名映射 + 独立限流器。"""
    vip_method_name: str           # "income_vip" / "balancesheet_vip" / "cashflow_vip"
    by_code_method_name: str       # "income" / "balancesheet" / "cashflow"
    column_map_attr: str           # "report_income_column_map" / ...
    rate_limit: Callable[[], None] # 400/min per endpoint


_TUSHARE_REPORT_SPECS: dict[str, _TushareReportSpec] = {
    "income": _TushareReportSpec(
        vip_method_name="income_vip",
        by_code_method_name="income",
        column_map_attr="report_income_column_map",
        rate_limit=create_rate_limiter(400),
    ),
    "balance": _TushareReportSpec(
        vip_method_name="balancesheet_vip",
        by_code_method_name="balancesheet",
        column_map_attr="report_balance_column_map",
        rate_limit=create_rate_limiter(400),
    ),
    "cashflow": _TushareReportSpec(
        vip_method_name="cashflow_vip",
        by_code_method_name="cashflow",
        column_map_attr="report_cashflow_column_map",
        rate_limit=create_rate_limiter(400),
    ),
    "indicator": _TushareReportSpec(
        vip_method_name="fina_indicator_vip",
        by_code_method_name="fina_indicator",
        column_map_attr="report_indicator_column_map",
        rate_limit=create_rate_limiter(200),
    ),
}


def _resolve(report_type: str) -> _TushareReportSpec:
    spec = _TUSHARE_REPORT_SPECS.get(report_type)
    if spec is None:
        raise ValueError(
            f"report_type 须为 {tuple(_TUSHARE_REPORT_SPECS)} 之一，收到: {report_type!r}"
        )
    return spec


class TushareReportClient:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    @staticmethod
    def _ensure_dataframe(df) -> pd.DataFrame:
        if df is None:
            return pd.DataFrame()
        if isinstance(df, pd.DataFrame):
            return df
        return pd.DataFrame(df)

    def pull(self, report_type: str, **kwargs) -> pd.DataFrame:
        """按期次拉 VIP 接口（period= 必传，由调用方传入）。"""
        spec = _resolve(report_type)
        spec.rate_limit()
        raw = self._ensure_dataframe(
            call_with_network_retry(getattr(self.ts, spec.vip_method_name), **kwargs)
        )
        return apply_source_column_map(raw, getattr(tushare_entities, spec.column_map_attr))

    def pull_by_code(self, report_type: str, ts_code: str, **kwargs) -> pd.DataFrame:
        """按个股拉普通接口（ts_code + end_date）。"""
        spec = _resolve(report_type)
        spec.rate_limit()
        raw = self._ensure_dataframe(
            call_with_network_retry(
                getattr(self.ts, spec.by_code_method_name), ts_code=ts_code, **kwargs
            )
        )
        return apply_source_column_map(raw, getattr(tushare_entities, spec.column_map_attr))
