"""个股资金流向 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

MONEYFLOW_COLUMNS: tuple[str, ...] = (
    "ts_code", "trade_date",
    "buy_sm_vol", "buy_sm_amount",
    "sell_sm_vol", "sell_sm_amount",
    "buy_md_vol", "buy_md_amount",
    "sell_md_vol", "sell_md_amount",
    "buy_lg_vol", "buy_lg_amount",
    "sell_lg_vol", "sell_lg_amount",
    "buy_elg_vol", "buy_elg_amount",
    "sell_elg_vol", "sell_elg_amount",
    "net_mf_vol", "net_mf_amount",
)

_NUMERIC_COLS = tuple(c for c in MONEYFLOW_COLUMNS if c not in ("ts_code", "trade_date"))


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_moneyflow(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in MONEYFLOW_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("ts_code", "trade_date") else ""

    return out[list(MONEYFLOW_COLUMNS)].reset_index(drop=True)
