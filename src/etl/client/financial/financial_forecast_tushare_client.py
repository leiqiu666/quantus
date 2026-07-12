"""业绩预告 Tushare Client（forecast_vip）。"""

from src.common.tushare_client import TushareClient
from src.common.function import create_rate_limiter
import pandas as pd

FORECAST_COLUMNS = [
    "ts_code", "ann_date", "end_date", "type",
    "p_change_min", "p_change_max", "net_profit_min", "net_profit_max",
    "last_parent_net", "first_ann_date", "summary", "change_reason",
]

_acquire_forecast_rate_limit = create_rate_limiter(200)


def finalize_forecast(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "ann_date" in out.columns:
        out["ann_date"] = out["ann_date"].astype(str).str.strip()
    if "end_date" in out.columns:
        out["end_date"] = out["end_date"].astype(str).str.strip()
    if "first_ann_date" in out.columns:
        out["first_ann_date"] = out["first_ann_date"].astype(str).str.strip()
    if "type" in out.columns:
        out["type"] = out["type"].astype(str).str.strip()

    return out


class TushareForecastClient:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_forecast_vip_by_period(self, period: str) -> pd.DataFrame:
        _acquire_forecast_rate_limit()
        df = self.ts.forecast_vip(
            period=period,
            fields=",".join(FORECAST_COLUMNS),
        )
        return finalize_forecast(df)
