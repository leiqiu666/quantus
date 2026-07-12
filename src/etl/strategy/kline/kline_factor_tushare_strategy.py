"""Tushare 技术因子 Strategy：按日区间增量拉取 → 按月 Parquet 写入。"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from src.common.function import create_rate_limiter, tqdm_iter
from src.common.setting import settings
from src.etl.extract.kline.kline_factor_tushare_extract import TushareFactorExtract
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
    TradeCalLocalExtract,
)
from src.etl.load.kline.kline_factor_parquet_load import TushareFactorParquetLoad
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.transform.kline.kline_factor_transform import TushareFactorTransform


class TushareFactorStrategy:
    def __init__(self) -> None:
        self._extract = TushareFactorExtract()
        self._transform = TushareFactorTransform()
        self._load = TushareFactorParquetLoad()
        self._trade_cal_strategy = TradeCalStrategy()
        self._acquire = create_rate_limiter(30)

    def pull_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        start = start_date or settings.etl_start_date("kline_daily")
        end = end_date or datetime.now().strftime("%Y%m%d")

        self._trade_cal_strategy.ensure_trade_cal(start_date=start, end_date=end)

        open_dates = TradeCalLocalExtract().get_open_trade_dates(
            start_date=start, end_date=end, exchange="SSE"
        )
        if not open_dates:
            print("无可用交易日")
            return 0

        existing = self._load.read_existing_trade_dates()
        current_month = datetime.now().strftime("%Y%m")
        # 当月日期始终重拉（数据可能更新）
        targets = [
            d for d in open_dates
            if d not in existing or d[:6] == current_month
        ]

        if not targets:
            print("Tushare 技术因子：无需拉取（已全部覆盖）")
            return 0

        buffer: list[pl.DataFrame] = []
        prev_ym: str | None = None
        total_rows = 0
        flushed_months: set[str] = set()

        _KEY_COLS = {"ts_code", "trade_date"}

        def _normalize_schema(df: pl.DataFrame) -> pl.DataFrame:
            return df.cast({
                col: pl.Float64
                for col in df.columns
                if col not in _KEY_COLS and df.schema[col] != pl.Float64
            })

        def _flush(ym: str) -> None:
            nonlocal total_rows
            if not buffer:
                return
            merged = pl.concat([_normalize_schema(b) for b in buffer])
            rows = self._load.write_month_partition(merged, ym)
            total_rows += rows
            flushed_months.add(ym)
            buffer.clear()

        for td in tqdm_iter(targets, desc="拉取 Tushare 技术因子"):
            ym = td[:6]
            if prev_ym and ym != prev_ym:
                _flush(prev_ym)

            self._acquire()
            pdf = self._extract.pull_by_date(td)
            pdf = self._transform.transform(pdf)
            if pdf.empty:
                prev_ym = ym
                continue

            buffer.append(pl.from_pandas(pdf))
            prev_ym = ym

        if prev_ym:
            _flush(prev_ym)

        print(
            f"Tushare 技术因子：拉取完成，{len(targets)} 个交易日，"
            f"写入 {len(flushed_months)} 个月分区，共 {total_rows} 行"
        )
        return total_rows
