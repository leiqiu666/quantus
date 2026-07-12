"""技术面因子 Client 共用工具。"""

from __future__ import annotations

from typing import Dict

import pandas as pd

# stk_factor_pro 后复权字段 → stk_factor 标准字段名映射
STK_FACTOR_PRO_TO_STD: Dict[str, str] = {
    "ts_code": "ts_code",
    "trade_date": "trade_date",
    "macd_dif_hfq": "macd_dif",
    "macd_dea_hfq": "macd_dea",
    "macd_hfq": "macd",
    "kdj_k_hfq": "kdj_k",
    "kdj_d_hfq": "kdj_d",
    "kdj_hfq": "kdj_j",
    "rsi_hfq_6": "rsi_6",
    "rsi_hfq_12": "rsi_12",
    "rsi_hfq_24": "rsi_24",
    "boll_upper_hfq": "boll_upper",
    "boll_mid_hfq": "boll_mid",
    "boll_lower_hfq": "boll_lower",
    "cci_hfq": "cci",
}

STK_FACTOR_PRO_FIELDS: list[str] = list(STK_FACTOR_PRO_TO_STD.keys())
STK_FACTOR_STD_COLUMNS: tuple[str, ...] = tuple(STK_FACTOR_PRO_TO_STD.values())

_NUMERIC_COLS = tuple(c for c in STK_FACTOR_STD_COLUMNS if c not in ("ts_code", "trade_date"))


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_stk_factor(df: pd.DataFrame | None) -> pd.DataFrame:
    """从 stk_factor_pro 原始字段提取技术指标并重命名为标准列名。"""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.rename(columns=STK_FACTOR_PRO_TO_STD)
    # 丢弃未映射的列
    out = out[[c for c in STK_FACTOR_STD_COLUMNS if c in out.columns]].copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in STK_FACTOR_STD_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("ts_code", "trade_date") else ""

    return out[list(STK_FACTOR_STD_COLUMNS)].reset_index(drop=True)
