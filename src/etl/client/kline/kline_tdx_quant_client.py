"""通达信 tdx_quant K 线 Client（经 HTTP 调用 quantus-api）。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from tqdm import tqdm

from src.common.setting import settings
from src.common.tdx_client import TdxClient
from src.etl.client.kline.kline_common import finalize_kline_daily
from src.etl.client.kline.kline_protocol import NotSupportedError
from src.service.stock.stock_base_service import StockBaseService

_MAX_BARS = 24000
_STOCK_CHUNK_SIZE = 500
# 按日全市场只取 OHLCV+Amount，减少回传体积
_DAILY_BY_DATE_FIELDS = ["Open", "High", "Low", "Close", "Volume", "Amount"]

_VALID_PERIODS = frozenset(
    {"5m", "15m", "30m", "1h", "1d", "1w", "1mon", "1m", "10m", "45d", "1q", "1y"}
)

_MINUTE_PERIODS = frozenset({"1m", "5m", "10m", "15m", "30m", "1h"})

_FIELD_MAP = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "vol",
    "Amount": "amount",
    "ForwardFactor": "forward_factor",
}

_OUTPUT_COLUMNS = [
    "ts_code",
    "trade_date",
    "trade_time",
    "open",
    "high",
    "low",
    "close",
    "vol",
    "amount",
    "forward_factor",
]


def _normalize_time_key(value: str) -> str:
    s = str(value).strip().replace("-", "").replace(":", "").replace(" ", "")
    if len(s) >= 14:
        return s[:14]
    if len(s) >= 8:
        return s[:8]
    return s


def _time_keys_ordered(start: str, end: str) -> bool:
    if not start or not end:
        return True
    return _normalize_time_key(start) <= _normalize_time_key(end)


def _is_minute_period(period: str) -> bool:
    return period.lower() in _MINUTE_PERIODS


def _retreat_end_time(first_dt: datetime, period: str) -> str:
    p = period.lower()
    if p in {"1d", "45d"}:
        prev = first_dt - timedelta(days=1)
        return prev.strftime("%Y%m%d")
    if p == "1w":
        prev = first_dt - timedelta(weeks=1)
        return prev.strftime("%Y%m%d")
    if p == "1mon":
        month = first_dt.month - 1
        year = first_dt.year
        if month < 1:
            month = 12
            year -= 1
        day = min(first_dt.day, 28)
        prev = first_dt.replace(year=year, month=month, day=day)
        return prev.strftime("%Y%m%d")
    if p == "1q":
        prev = first_dt - timedelta(days=90)
        return prev.strftime("%Y%m%d")
    if p == "1y":
        prev = first_dt.replace(year=first_dt.year - 1)
        return prev.strftime("%Y%m%d")
    if p == "1m":
        prev = first_dt - timedelta(minutes=1)
    elif p == "5m":
        prev = first_dt - timedelta(minutes=5)
    elif p == "10m":
        prev = first_dt - timedelta(minutes=10)
    elif p == "15m":
        prev = first_dt - timedelta(minutes=15)
    elif p == "30m":
        prev = first_dt - timedelta(minutes=30)
    elif p == "1h":
        prev = first_dt - timedelta(hours=1)
    else:
        prev = first_dt - timedelta(days=1)
        return prev.strftime("%Y%m%d")
    return prev.strftime("%Y%m%d%H%M%S")


def _filter_by_date_range(
    df: pd.DataFrame,
    start: str,
    end: str,
    period: str,
) -> pd.DataFrame:
    if df.empty:
        return df

    sk = _normalize_time_key(start)
    ek = _normalize_time_key(end)
    if _is_minute_period(period):
        col = df["trade_time"].astype(str).map(_normalize_time_key)
        sk = (sk + "000000")[:12] if len(sk) <= 8 else sk[:12]
        ek = (ek + "235959")[:12] if len(ek) <= 8 else ek[:12]
    else:
        col = df["trade_date"].astype(str).map(lambda x: _normalize_time_key(x)[:8])
        sk, ek = sk[:8], ek[:8]

    return df[(col >= sk) & (col <= ek)].reset_index(drop=True)


def _batch_bar_count(raw: dict[str, pd.DataFrame]) -> int:
    close_df = raw.get("Close")
    if close_df is None or close_df.empty:
        return 0
    return int(len(close_df.index))


def _raw_wide_to_long_daily(
    raw: dict[str, pd.DataFrame],
    trade_date: str,
) -> pd.DataFrame:
    """将 get_market_data 宽表（index=日期, columns=股票）转为 long 格式（向量化）。"""
    close_df = raw.get("Close")
    if close_df is None or close_df.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    td_key = _normalize_time_key(trade_date)[:8]
    if len(close_df.index) == 1:
        row_i = 0
    else:
        idx_keys = pd.Index(close_df.index).strftime("%Y%m%d")
        matches = (idx_keys == td_key).nonzero()[0]
        if matches.size == 0:
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)
        row_i = int(matches[0])

    close_row = close_df.iloc[row_i]
    valid_codes = close_row.index[close_row.notna()]
    if len(valid_codes) == 0:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    n = len(valid_codes)
    data: dict[str, object] = {
        "ts_code": [str(c) for c in valid_codes],
        "trade_date": [td_key] * n,
        "trade_time": [""] * n,
    }
    for src_field, dst_col in _FIELD_MAP.items():
        if dst_col == "forward_factor":
            continue
        field_df = raw.get(src_field)
        if field_df is None or row_i >= len(field_df.index):
            data[dst_col] = [pd.NA] * n
            continue
        # 一次取整行 + reindex 到 valid_codes，避免 .iloc[i][code] 双重索引
        field_row = field_df.iloc[row_i].reindex(valid_codes)
        data[dst_col] = [None if pd.isna(v) else float(v) for v in field_row.tolist()]

    out = pd.DataFrame(data)
    for col in _OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[_OUTPUT_COLUMNS]


def _raw_to_dataframe(
    raw: dict[str, pd.DataFrame],
    stock_list: list[str],
    period: str,
) -> pd.DataFrame:
    """将 get_market_data 宽表批量转为 long 格式（向量化 stack 路径）。"""
    if not raw or "Close" not in raw:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    close_df = raw["Close"]
    if close_df.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    code_set = [c for c in stock_list if c in close_df.columns]
    if not code_set:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    # 仅保留 stock_list ∩ close 列；按 stock_list 顺序，便于下游 dedupe(keep="first") 行为稳定
    close_sub = close_df[code_set]
    # close 非 NaN 的 (date, code) 即为本批次有效行集合
    close_long = close_sub.stack().dropna().rename("close")
    if close_long.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    minute = _is_minute_period(period)
    out = close_long.reset_index()
    out.columns = ["__dt", "ts_code", "close"]

    # 其余 OHLCV / Amount 字段：按各自 stack 后 reindex 到 close_long 的 MultiIndex
    for src_field, dst_col in _FIELD_MAP.items():
        if dst_col == "close":
            continue  # 已包含
        field_df = raw.get(src_field)
        if field_df is None:
            out[dst_col] = pd.NA
            continue
        avail = [c for c in code_set if c in field_df.columns]
        if not avail:
            out[dst_col] = pd.NA
            continue
        field_long = field_df[avail].stack().rename(dst_col)
        out[dst_col] = field_long.reindex(close_long.index).to_numpy()

    out["ts_code"] = out["ts_code"].astype(str)
    if minute:
        out["trade_time"] = out["__dt"].dt.strftime("%Y%m%d%H%M")
        out["trade_date"] = out["__dt"].dt.strftime("%Y%m%d")
    else:
        out["trade_date"] = out["__dt"].dt.strftime("%Y%m%d")
        out["trade_time"] = ""
    out = out.drop(columns=["__dt"])

    for col in _OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[_OUTPUT_COLUMNS]


def _dedupe_kline(df: pd.DataFrame, period: str) -> pd.DataFrame:
    if df.empty:
        return df
    if _is_minute_period(period):
        subset = ["ts_code", "trade_time"]
    else:
        subset = ["ts_code", "trade_date"]
    return df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)


def _build_stock_list_for_date(trade_date: str, stock_rows: list | None = None) -> list[str]:
    """从本地 stock_list 筛选 trade_date 当日已上市且未退市的 A 股代码。"""
    td = (trade_date or "").strip()
    if not td:
        return []

    if stock_rows is None:
        stock_rows = StockBaseService().get_all_stock_list_a()

    codes: list[str] = []
    for inst in stock_rows:
        code = getattr(inst, "ts_code", None)
        if not code:
            continue
        list_date = str(getattr(inst, "list_date", None) or "").strip()
        delist_date = str(getattr(inst, "delist_date", None) or "").strip()
        if list_date and list_date > td:
            continue
        if delist_date and delist_date < td:
            continue
        codes.append(str(code).strip())
    return codes


class TdxQuantKlineClient:
    def __init__(self) -> None:
        self.tdx_quant_client = TdxClient()
        self._stock_rows_cache: list | None = None

    def pull_kline_daily_range(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        raw = self.pull_kline_range(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period="1d",
        )
        return finalize_kline_daily(raw, amount_in_wan_yuan=True)

    def pull_kline_adj_factor_range(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        raise NotSupportedError("tdx_quant Client 暂不支持 adj_factor 拉取")

    def pull_kline_adj_factor_by_trade_date(
        self,
        *,
        trade_date: str,
    ) -> pd.DataFrame:
        raise NotSupportedError("tdx_quant Client 暂不支持 adj_factor 按日全市场拉取")

    def pull_kline_stk_limit_range(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        raise NotSupportedError("tdx_quant Client 暂不支持 stk_limit 拉取")

    def pull_kline_stk_limit_by_trade_date(
        self,
        *,
        trade_date: str,
    ) -> pd.DataFrame:
        raise NotSupportedError("tdx_quant Client 暂不支持 stk_limit 按日全市场拉取")

    def pull_kline_daily_by_trade_date(
        self,
        *,
        trade_date: str,
    ) -> pd.DataFrame:
        """
        按交易日拉取全市场日线（与 Tushare 相同签名：仅 trade_date）。

        经 tdx_quant HTTP API 调用 get_market_data(stock_list=全市场)。
        """
        td = (trade_date or "").strip()
        if not td:
            return pd.DataFrame()

        if not settings.tdx_api_host.strip():
            return pd.DataFrame()

        if self._stock_rows_cache is None:
            self._stock_rows_cache = StockBaseService().get_all_stock_list_a()

        codes = _build_stock_list_for_date(td, self._stock_rows_cache)
        if not codes:
            return pd.DataFrame()

        try:
            normalized = self.tdx_quant_client.normalize_stock_codes(codes)
        except ValueError:
            return pd.DataFrame()

        batch = self._fetch_daily_by_date(trade_date=td, stock_list=normalized)
        if batch.empty:
            return pd.DataFrame()

        td_key = _normalize_time_key(td)[:8]
        batch = batch[
            batch["trade_date"].astype(str).map(lambda x: _normalize_time_key(x)[:8]) == td_key
        ].reset_index(drop=True)
        batch = _dedupe_kline(batch, "1d")
        return finalize_kline_daily(batch, amount_in_wan_yuan=True)

    def _fetch_daily_by_date(
        self,
        *,
        trade_date: str,
        stock_list: list[str],
    ) -> pd.DataFrame:
        """全市场单次 get_market_data（count=1）；失败时尝试区间模式。"""
        try:
            raw = self.tdx_quant_client.get_market_data(
                field_list=_DAILY_BY_DATE_FIELDS,
                stock_list=stock_list,
                period="1d",
                start_time="",
                end_time=trade_date,
                count=1,
                dividend_type="none",
                fill_data=True,
            )
            batch = _raw_wide_to_long_daily(raw, trade_date)
            if not batch.empty:
                return batch
        except Exception as exc:
            tqdm.write(
                f"[警告] tdx_quant get_market_data count=1 失败 "
                f"trade_date={trade_date}: {exc}; 回退区间模式"
            )

        try:
            raw = self.tdx_quant_client.get_market_data(
                field_list=_DAILY_BY_DATE_FIELDS,
                stock_list=stock_list,
                period="1d",
                start_time=trade_date,
                end_time=trade_date,
                count=-1,
                dividend_type="none",
                fill_data=True,
            )
            return _raw_wide_to_long_daily(raw, trade_date)
        except Exception as exc:
            tqdm.write(
                f"[警告] tdx_quant get_market_data 区间模式失败 "
                f"trade_date={trade_date}: {exc}"
            )
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    def pull_kline_range(
        self,
        *,
        ts_code: str | list[str],
        start_date: str,
        end_date: str,
        period: str,
        dividend_type: str = "none",
    ) -> pd.DataFrame:
        """
        拉取 [start_date, end_date] 内 K 线并归一化为 long DataFrame。

        历史区间须先在通达信客户端「系统 → 盘后数据下载」对应周期数据。
        """
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        p = (period or "").strip().lower()

        if not start or not end or not _time_keys_ordered(start, end):
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)
        if p not in _VALID_PERIODS:
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)

        try:
            stock_list = self.tdx_quant_client.normalize_stock_codes(ts_code)
        except ValueError:
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)

        parts: list[pd.DataFrame] = []
        cur_end = end

        while True:
            raw = self.tdx_quant_client.get_market_data(
                stock_list=stock_list,
                period=p,
                start_time="",
                end_time=cur_end,
                count=_MAX_BARS,
                dividend_type=dividend_type,
                fill_data=True,
            )
            batch = _filter_by_date_range(
                _raw_to_dataframe(raw, stock_list, p),
                start,
                end,
                p,
            )
            bar_count = _batch_bar_count(raw)

            if bar_count == 0:
                break

            if not batch.empty:
                parts.append(batch)

            if bar_count < _MAX_BARS:
                break

            first_idx = raw["Close"].index.min()
            if not isinstance(first_idx, pd.Timestamp):
                first_idx = pd.Timestamp(first_idx)
            prev_end = _retreat_end_time(first_idx.to_pydatetime(), p)
            if _normalize_time_key(prev_end) < _normalize_time_key(start):
                break
            if _normalize_time_key(prev_end) >= _normalize_time_key(cur_end):
                break
            cur_end = prev_end

        if not parts:
            return pd.DataFrame(columns=_OUTPUT_COLUMNS)

        out = pd.concat(parts, ignore_index=True)
        return _dedupe_kline(out, p)
