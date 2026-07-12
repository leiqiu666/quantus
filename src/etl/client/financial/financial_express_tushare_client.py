"""业绩快报 Tushare Client（express_vip）。"""

from src.common.tushare_client import TushareClient
from src.common.function import create_rate_limiter
import pandas as pd

EXPRESS_COLUMNS = [
    "ts_code", "ann_date", "end_date",
    "revenue", "operate_profit", "total_profit", "n_income",
    "total_assets", "total_hldr_eqy_exc_min_int",
    "diluted_eps", "diluted_roe", "yoy_net_profit", "bps",
    "yoy_sales", "yoy_op", "yoy_tp", "yoy_dedu_np",
    "yoy_eps", "yoy_roe", "growth_assets", "yoy_equity",
]

_acquire_express_rate_limit = create_rate_limiter(200)


def finalize_express(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "ann_date" in out.columns:
        out["ann_date"] = out["ann_date"].astype(str).str.strip()
    if "end_date" in out.columns:
        out["end_date"] = out["end_date"].astype(str).str.strip()

    return out


class TushareExpressClient:
    def __init__(self):
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_express_vip_by_period(self, period: str) -> pd.DataFrame:
        _acquire_express_rate_limit()
        df = self.ts.express_vip(
            period=period,
            fields=",".join(EXPRESS_COLUMNS),
        )
        return finalize_express(df)
