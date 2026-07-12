"""ETL 增量起点：{DB表名}_START_DATE / _START_MONTH + ETL_DEFAULT_START_DATE 兜底。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Final

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

# table key（snake_case DB 表名）→ 已废弃的旧 env 名（兼容 .env 未迁移）
_START_DATE_LEGACY: Final[dict[str, str]] = {
    "financial_report": "REPORT_START_DATE",
    "stock_trade_calendar": "TRADE_CAL_START_DATE",
    "stock_suspend": "SUSPEND_START_DATE",
    "stock_premarket": "STOCK_PREMARKET_START_DATE",
    "stock_share_float": "STOCK_SHARE_FLOAT_START_DATE",
    "market_daily_basic": "DAILY_BASIC_START_DATE",
    "market_dividend": "DIVIDEND_START_DATE",
    "kline_stock_factor": "STK_FACTOR_START_DATE",
    "market_moneyflow": "MONEYFLOW_START_DATE",
    "market_margin_detail": "MARGIN_START_DATE",
    "market_northbound_top10": "HSGT_START_DATE",
    "market_moneyflow_hsgt": "HSGT_FLOW_START_DATE",
    "market_hk_hold": "HK_HOLD_START_DATE",
    "financial_stock_holder": "STK_HOLDER_START_DATE",
    "market_dragon_tiger": "DRAGON_TIGER_START_DATE",
    "market_block_trade": "BLOCK_TRADE_START_DATE",
    "financial_shareholder_top10": "SHAREHOLDER_START_DATE",
    "financial_forecast": "FORECAST_START_DATE",
    "financial_express": "EXPRESS_START_DATE",
    "financial_audit": "AUDIT_START_DATE",
    "financial_disclosure_date": "DISCLOSURE_DATE_START_DATE",
    "financial_top10_floatholders": "TOP10_FLOATHOLDERS_START_DATE",
    "financial_fina_mainbz": "FINA_MAINBZ_START_DATE",
}

# 未配置 env 时的业务硬编码默认（不走 ETL_DEFAULT_START_DATE）
_START_DATE_SPECIAL: Final[dict[str, str]] = {
    "kline_stk_limit": "20090601",  # 创业板开板日
}


@lru_cache
def _ensure_dotenv_loaded() -> None:
    """pydantic-settings 读 .env 但不写入 os.environ，此处补一次 load_dotenv。"""
    try:
        from dotenv import load_dotenv

        if _ENV_FILE.is_file():
            load_dotenv(_ENV_FILE, override=False)
    except ImportError:
        pass


def _read_env(key: str) -> str:
    _ensure_dotenv_loaded()
    return (os.getenv(key) or "").strip()


def read_table_start_date(table: str) -> str | None:
    """只读 env（新名 + legacy），无则返回 None。"""
    table = table.strip().lower()
    val = _read_env(f"{table.upper()}_START_DATE")
    if val:
        return val
    legacy = _START_DATE_LEGACY.get(table)
    if legacy:
        val = _read_env(legacy)
        if val:
            return val
    return None


def resolve_etl_start_date(
    table: str,
    default: str,
    *,
    fallback_table: str | None = None,
) -> str:
    """
    解析 ETL 增量起点。

    优先级：{TABLE}_START_DATE → legacy env → fallback_table 链 → 特殊默认 → default（ETL_DEFAULT_START_DATE）。
    """
    table = table.strip().lower()
    direct = read_table_start_date(table)
    if direct:
        return direct
    if fallback_table:
        fb = read_table_start_date(fallback_table)
        if fb:
            return fb
    special = _START_DATE_SPECIAL.get(table)
    if special:
        return special
    return default


def resolve_etl_start_month(table: str, default: str) -> str:
    """按月增量：{TABLE}_START_MONTH → default 的 YYYYMM。"""
    table = table.strip().lower()
    val = _read_env(f"{table.upper()}_START_MONTH")
    if val:
        return val
    legacy = _START_DATE_LEGACY.get(table)
    if legacy:
        val = _read_env(legacy)
        if val:
            return val
    d = (default or "").strip()
    return d[:6] if len(d) >= 6 else d
