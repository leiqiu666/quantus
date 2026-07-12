"""K 线日线查询服务（仅读库，不依赖 ETL）。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.model.kline.kline_daily_model import KlineDailyModel
from src.model.kline.kline_daily_period_count_model import KlineDailyPeriodCountModel
from src.service.stock.stock_active_count_service import StockActiveCountService


def _ymd_add_days(ymd: str, days: int) -> str:
    d = datetime.strptime(ymd.strip(), "%Y%m%d").date()
    return (d + timedelta(days=days)).strftime("%Y%m%d")


class KlineDailyService:
    def __init__(self) -> None:
        self._model = KlineDailyModel()
        self._period_count_model = KlineDailyPeriodCountModel()
        self._active_count_service = StockActiveCountService()

    def get_max_trade_date(self) -> str | None:
        """kline_daily 表已入库的最大 trade_date。"""
        return self._model.get_max_trade_date()

    def resolve_incremental_start(self, configured_start: str) -> str:
        """增量拉取起点：max(配置起始日, 库内最大 trade_date 的下一自然日)。"""
        floor = (configured_start or "").strip()
        if not floor:
            return ""

        last = self.get_max_trade_date()
        if not last:
            return floor
        return max(floor, _ymd_add_days(last, 1))

    def list_trade_date_kline_counts(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """kline_daily 按 trade_date 聚合的条数列表（不含快照 period_stock_count）。"""
        return self._model.get_trade_date_list(
            start_date=start_date,
            end_date=end_date,
        )

    def list_kline_daily_by_trade_date(self, trade_date: str) -> List[Dict[str, Any]]:
        """指定交易日 kline_daily 全行。"""
        return self._model.list_by_trade_date(trade_date)

    def get_trade_date_list(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        以 kline_daily_period_count 快照提供开市日行列表；
        period_stock_count 取自 stock_active_count.trading_count；
        kline_daily_count 实时聚合 kline_daily；
        kline_adj_factor_count 实时聚合 kline_daily.adj_factor 非空行；
        kline_stk_limit_count 实时聚合 up_limit、down_limit 均已入库行。
        列表按 trade_date 倒序（新到旧）。
        """
        snapshot_rows = self._period_count_model.list_by_range(
            start_date=start_date,
            end_date=end_date,
        )
        if not snapshot_rows:
            return []

        trade_dates = [row["trade_date"] for row in snapshot_rows]
        stock_counts = self._active_count_service.resolve_trading_counts(trade_dates)

        daily_by_date = {
            row["trade_date"]: int(row.get("kline_daily_count") or 0)
            for row in self._model.get_trade_date_list(
                start_date=start_date,
                end_date=end_date,
            )
        }
        adj_by_date = {
            row["trade_date"]: int(row.get("kline_adj_factor_count") or 0)
            for row in self.list_trade_date_adj_factor_counts(
                start_date=start_date,
                end_date=end_date,
            )
        }
        limit_by_date = {
            row["trade_date"]: int(row.get("kline_stk_limit_count") or 0)
            for row in self.list_trade_date_stk_limit_counts(
                start_date=start_date,
                end_date=end_date,
            )
        }
        return [
            {
                "trade_date": row["trade_date"],
                "period_stock_count": int(
                    stock_counts.get(row["trade_date"], 0)
                ),
                "kline_daily_count": daily_by_date.get(row["trade_date"], 0),
                "kline_adj_factor_count": adj_by_date.get(row["trade_date"], 0),
                "kline_stk_limit_count": limit_by_date.get(row["trade_date"], 0),
            }
            for row in snapshot_rows
        ]

    def list_kline_daily_period_count(self) -> List[Dict[str, Any]]:
        """查询 kline_daily_period_count 表全部记录。"""
        return self._period_count_model.list_all()

    def get_trade_dates_with_adj_factor_by_ts_code(
        self,
        ts_code: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """单股在区间内 kline_daily.adj_factor 非空的 trade_date 列表（升序）。"""
        return self._model.get_trade_dates_with_adj_factor_by_ts_code(
            ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def list_trade_date_adj_factor_counts(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """kline_daily.adj_factor 非空行按 trade_date 聚合的条数列表。"""
        return self._model.get_trade_date_adj_factor_count_list(
            start_date=start_date,
            end_date=end_date,
        )

    def get_trade_dates_with_stk_limit_by_ts_code(
        self,
        ts_code: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """单股在区间内 up_limit、down_limit 均已入库的 trade_date 列表（升序）。"""
        return self._model.get_trade_dates_with_stk_limit_by_ts_code(
            ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def list_trade_date_stk_limit_counts(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """kline_daily 涨跌停齐全行按 trade_date 聚合的条数列表。"""
        return self._model.get_trade_date_stk_limit_count_list(
            start_date=start_date,
            end_date=end_date,
        )

    def get_trade_dates_by_ts_code(
        self,
        ts_code: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """单股在区间内已入库的 trade_date 列表（升序）。"""
        return self._model.get_trade_dates_by_ts_code(
            ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def list_resolved_trade_dates_grouped(
        self,
        *,
        dimension: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        全市场按维度一次性返回 {ts_code: [trade_date, ...]}，供完整性校验
        替代 get_trade_dates_*_by_ts_code 的 N+1 查询。
        """
        return self._model.list_resolved_trade_dates_grouped(
            dimension=dimension,
            start_date=start_date,
            end_date=end_date,
        )
