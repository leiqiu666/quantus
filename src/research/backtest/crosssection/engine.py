"""截面回测引擎。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import polars as pl

from src.common.setting import settings
from src.research.backtest.common.calendar import RebalanceCalendar
from src.research.backtest.common.cost import CostModel
from src.research.backtest.common.portfolio import filter_and_renorm, turnover_and_cost
from src.research.dataset.factor import FactorDataset
from src.research.dataset.kline import KlineDataset
from src.research.dataset.universe import UniverseDataset
from src.research.performance.ic import calc_ic_row, ic_summary
from src.research.performance.report import print_summary, write_backtest_output
from src.research.performance.returns import metrics_from_frame
from src.research.strategy.single_factor import SingleFactorStrategy


@dataclass
class BacktestResult:
    daily_returns: pl.DataFrame
    portfolio_history: pl.DataFrame
    trades: pl.DataFrame
    ic_series: pl.DataFrame
    summary: dict = field(default_factory=dict)
    output_dir: str | None = None


class CrossSectionEngine:
    def __init__(
        self,
        strategy: SingleFactorStrategy | object,
        universe: UniverseDataset | None = None,
        cost_model: CostModel | None = None,
        rebalance_freq: str = "monthly",
        n_groups: int | None = None,
        warehouse_root: str | None = None,
    ) -> None:
        self.strategy = strategy
        self.universe = universe or UniverseDataset()
        self.cost_model = cost_model or CostModel()
        self.rebalance_freq = rebalance_freq
        if n_groups is not None:
            self.strategy.n_groups = n_groups
        self._n_groups = self.strategy.n_groups
        self._root = Path(warehouse_root or settings.warehouse_root)
        self._factors = FactorDataset(str(self._root))
        self._kline = KlineDataset(str(self._root))
        self._calendar = RebalanceCalendar()

    def run(self, start: str, end: str) -> BacktestResult:
        start = (start or "").strip()
        end = (end or "").strip()
        if not start or not end or start > end:
            raise ValueError(f"无效回测区间: {start}~{end}")

        open_dates = self._calendar.open_dates(start, end)
        rebalance_dates = self._calendar.rebalance_dates(
            start, end, self.rebalance_freq
        )
        if len(rebalance_dates) < 2:
            raise RuntimeError("调仓日不足 2 个，无法回测")

        # 预加载日 K（后复权收益 + 涨跌停约束）
        kline_lf = self._kline.read_range(start, end)
        # adj_factor 用于质量告警（列可能不存在）
        try:
            kline = kline_lf.collect()
        except Exception:
            kline = (
                kline_lf.select(
                    "ts_code",
                    "trade_date",
                    "close",
                    "close_adj",
                    "up_limit",
                    "down_limit",
                ).collect()
            )
        need = {"ts_code", "trade_date", "close", "close_adj", "up_limit", "down_limit"}
        missing_cols = [c for c in need if c not in kline.columns]
        if missing_cols:
            raise RuntimeError(f"日 K 缺列: {missing_cols}")
        if kline.is_empty():
            raise RuntimeError(f"日 K 为空: {start}~{end}")

        ret_map = self._build_daily_ret_map(kline)
        limit_blocked = self._build_limit_blocked(kline)

        group_ids = [f"G{i}" for i in range(self._n_groups)]
        holdings: dict[str, dict[str, float]] = {g: {} for g in group_ids}
        portfolio_rows: list[dict] = []
        trade_rows: list[dict] = []
        daily_rows: list[dict] = []
        ic_rows: list[dict] = []
        turnovers: list[float] = []
        turnover_rows: list[dict] = []
        n_rebalance_used = 0

        factor_name = self.strategy.factor_name
        factor_names = list(
            getattr(self.strategy, "factor_names", None) or [factor_name]
        )

        for i, td in enumerate(rebalance_dates[:-1]):
            next_td = rebalance_dates[i + 1]
            uni = self.universe.all_a(td)
            factor_cs = self._factors.read_multi(factor_names, td)
            if factor_cs.is_empty():
                holdings = {g: {} for g in group_ids}
                continue

            n_rebalance_used += 1
            raw_targets = self.strategy.target_weights(td, factor_cs, uni)
            blocked = limit_blocked.get(td, set())
            tradable = set(uni) - blocked

            costs_by_group: dict[str, float] = {}
            clean_holdings: dict[str, dict[str, float]] = {}
            day_turnover = 0.0
            for g in group_ids:
                filtered = filter_and_renorm(raw_targets.get(g, {}), tradable)
                to, cost, trades = turnover_and_cost(
                    holdings.get(g, {}), filtered, self.cost_model
                )
                day_turnover += to
                costs_by_group[g] = cost
                clean_holdings[g] = filtered
                for t in trades:
                    trade_rows.append(
                        {
                            "trade_date": td,
                            "group_id": g,
                            "ts_code": t["ts_code"],
                            "delta_weight": t["delta_weight"],
                            "cost": t["cost"],
                        }
                    )
                for code, w in filtered.items():
                    portfolio_rows.append(
                        {
                            "trade_date": td,
                            "group_id": g,
                            "ts_code": code,
                            "weight": w,
                        }
                    )
            holdings = clean_holdings
            avg_to = day_turnover / max(self._n_groups, 1)
            turnovers.append(avg_to)
            turnover_rows.append({"trade_date": td, "turnover": avg_to})

            # IC：因子（或综合分）vs 持有期收益（td → next_td）
            period_ret = self._holding_period_return(ret_map, open_dates, td, next_td)
            compose = getattr(self.strategy, "compose_scores", None)
            if callable(compose):
                scored = compose(factor_cs)
                fvals = {
                    r["ts_code"]: float(r["value"])
                    for r in scored.iter_rows(named=True)
                    if r.get("value") is not None and r["ts_code"] in uni
                }
            else:
                value_col = (
                    "value"
                    if "value" in factor_cs.columns
                    else factor_name
                )
                fvals = {
                    r["ts_code"]: float(r[value_col])
                    for r in factor_cs.iter_rows(named=True)
                    if r.get(value_col) is not None and r["ts_code"] in uni
                }
            ic, rank_ic = calc_ic_row(fvals, period_ret)
            ic_rows.append({"trade_date": td, "ic": ic, "rank_ic": rank_ic})

            # 日收益：开市日序列中 (td, next_td] —— 从 T→T+1 开始
            seg = [d for d in open_dates if td < d <= next_td]
            for j, day in enumerate(seg):
                row: dict = {"trade_date": day}
                group_rets = []
                for g in group_ids:
                    wmap = holdings.get(g, {})
                    r = 0.0
                    for code, w in wmap.items():
                        r += w * ret_map.get((code, day), 0.0)
                    if j == 0:
                        r -= costs_by_group.get(g, 0.0)
                    row[g] = r
                    group_rets.append(r)
                row["long_short"] = group_rets[0] - group_rets[-1] if group_rets else 0.0
                daily_rows.append(row)

        daily_df = pl.DataFrame(daily_rows) if daily_rows else pl.DataFrame(
            {"trade_date": pl.Series([], dtype=pl.Utf8)}
        )
        portfolio_df = pl.DataFrame(portfolio_rows) if portfolio_rows else pl.DataFrame(
            schema={
                "trade_date": pl.Utf8,
                "group_id": pl.Utf8,
                "ts_code": pl.Utf8,
                "weight": pl.Float64,
            }
        )
        trades_df = pl.DataFrame(trade_rows) if trade_rows else pl.DataFrame(
            schema={
                "trade_date": pl.Utf8,
                "group_id": pl.Utf8,
                "ts_code": pl.Utf8,
                "delta_weight": pl.Float64,
                "cost": pl.Float64,
            }
        )
        ic_df = pl.DataFrame(ic_rows) if ic_rows else pl.DataFrame(
            schema={"trade_date": pl.Utf8, "ic": pl.Float64, "rank_ic": pl.Float64}
        )

        ls_metrics = metrics_from_frame(daily_df, "long_short") if not daily_df.is_empty() else {}
        g0_metrics = metrics_from_frame(daily_df, "G0") if not daily_df.is_empty() and "G0" in daily_df.columns else {}
        ic_stats = ic_summary(ic_df)

        warnings = self._build_warnings(
            open_dates=open_dates,
            n_rebalance=n_rebalance_used,
            kline=kline,
            ret_map=ret_map,
        )

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
        if hasattr(self.strategy, "factor_names"):
            strategy_name = f"multi_factor_{factor_name}"
        else:
            strategy_name = f"single_factor_{factor_name}"
        out_dir = self._root / "backtest" / strategy_name / run_id

        cm = self.cost_model
        summary = {
            "strategy": strategy_name,
            "factor": factor_name,
            "start": start,
            "end": end,
            "rebalance": self.rebalance_freq,
            "groups": self._n_groups,
            "run_id": run_id,
            "avg_turnover": (sum(turnovers) / len(turnovers)) if turnovers else None,
            "n_rebalance": n_rebalance_used,
            "n_trade_days": len(open_dates),
            "benchmark": "000300.SH",
            "cost": {
                "commission_rate": cm.commission_rate,
                "stamp_duty_rate": cm.stamp_duty_rate,
                "slippage_rate": cm.slippage_rate,
            },
            "warnings": warnings,
            **ic_stats,
            "sharpe": ls_metrics.get("sharpe"),
            "annual_return": ls_metrics.get("annual_return"),
            "mdd": ls_metrics.get("mdd"),
            "calmar": ls_metrics.get("calmar"),
            "top_group_sharpe": g0_metrics.get("sharpe"),
            "output_dir": str(out_dir),
        }

        turnover_df = (
            pl.DataFrame(turnover_rows)
            if turnover_rows
            else pl.DataFrame(
                schema={"trade_date": pl.Utf8, "turnover": pl.Float64}
            )
        )

        write_backtest_output(
            out_dir,
            portfolio=portfolio_df,
            trades=trades_df,
            returns=daily_df,
            ic=ic_df,
            summary=summary,
            turnover=turnover_df,
        )
        print_summary(summary)

        return BacktestResult(
            daily_returns=daily_df,
            portfolio_history=portfolio_df,
            trades=trades_df,
            ic_series=ic_df,
            summary=summary,
            output_dir=str(out_dir),
        )

    @staticmethod
    def _build_warnings(
        *,
        open_dates: list[str],
        n_rebalance: int,
        kline: pl.DataFrame,
        ret_map: dict[tuple[str, str], float],
    ) -> list[str]:
        out: list[str] = []
        if n_rebalance < 3:
            out.append(f"调仓次数仅 {n_rebalance}（建议 ≥3），统计不稳定")
        if len(open_dates) < 60:
            out.append(f"开市日仅 {len(open_dates)}（建议 ≥60），短样本")

        # 任一日收益中位数异常
        by_day: dict[str, list[float]] = {}
        for (_code, d), r in ret_map.items():
            by_day.setdefault(d, []).append(r)
        for d, rs in by_day.items():
            if not rs:
                continue
            s = sorted(rs)
            mid = s[len(s) // 2]
            if abs(mid) > 0.20:
                out.append(f"{d} 全市场后复权收益中位数 {mid:.1%}，疑似复权异常")
                break

        if "adj_factor" in kline.columns:
            n = kline.height
            if n > 0:
                null_n = kline.filter(pl.col("adj_factor").is_null()).height
                if null_n / n > 0.05:
                    out.append(
                        f"区间内 adj_factor 空值占比 {null_n / n:.1%}（>5%），收益可能失真"
                    )
        return out

    @staticmethod
    def _build_daily_ret_map(kline: pl.DataFrame) -> dict[tuple[str, str], float]:
        """(ts_code, trade_date) -> close_adj / prev_close_adj - 1。"""
        df = kline.sort(["ts_code", "trade_date"]).with_columns(
            (
                pl.col("close_adj")
                / pl.col("close_adj").shift(1).over("ts_code")
                - 1.0
            ).alias("ret")
        )
        out: dict[tuple[str, str], float] = {}
        for row in df.select("ts_code", "trade_date", "ret").iter_rows(named=True):
            r = row["ret"]
            if r is None:
                continue
            out[(row["ts_code"], row["trade_date"])] = float(r)
        return out

    @staticmethod
    def _build_limit_blocked(kline: pl.DataFrame) -> dict[str, set[str]]:
        """trade_date -> 涨停或跌停不可买/卖的 ts_code（触板）。"""
        out: dict[str, set[str]] = {}
        cols = set(kline.columns)
        if "up_limit" not in cols or "down_limit" not in cols:
            return out
        for row in kline.select(
            "ts_code", "trade_date", "close", "up_limit", "down_limit"
        ).iter_rows(named=True):
            close = row["close"]
            up = row["up_limit"]
            down = row["down_limit"]
            if close is None:
                continue
            blocked = False
            if up is not None and close >= up * 0.999:
                blocked = True
            if down is not None and close <= down * 1.001:
                blocked = True
            if blocked:
                out.setdefault(row["trade_date"], set()).add(row["ts_code"])
        return out

    @staticmethod
    def _holding_period_return(
        ret_map: dict[tuple[str, str], float],
        open_dates: list[str],
        td: str,
        next_td: str,
    ) -> dict[str, float]:
        """从 T→T+1 复利到 next_td（含）。"""
        seg = [d for d in open_dates if td < d <= next_td]
        if not seg:
            return {}
        # 收集涉及的股票
        codes = {c for (c, d) in ret_map if d in seg}
        out: dict[str, float] = {}
        for code in codes:
            wealth = 1.0
            ok = False
            for d in seg:
                r = ret_map.get((code, d))
                if r is None:
                    continue
                wealth *= 1.0 + r
                ok = True
            if ok:
                out[code] = wealth - 1.0
        return out
