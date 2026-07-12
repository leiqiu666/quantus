"""K 线 Strategy 层：三维度（daily / adj_factor / stk_limit）共享同一份编排实现。"""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.common.function import format_micro_stock_postfix, scan_macro_snapshot_rows, tqdm_iter
from src.common.setting import settings
from src.etl.extract.local.kline.kline_local_extract import KlineLocalExtract
from src.etl.extract.local.stock.stock_suspend_local_extract import SuspendLocalExtract
from src.etl.extract.local.stock.stock_trade_calendar_local_extract import TradeCalLocalExtract
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.kline.kline_workflow import KlineWorkflow
from src.service.stock.stock_base_service import StockBaseService


def _effective_list_date(list_date: str | None, start_date: str | None) -> str | None:
    """取 max(上市日, start_date)；start_date 为空时不限制。"""
    floor = (start_date or "").strip()
    raw = (list_date or "").strip() if list_date else ""
    if not floor:
        return raw or None
    if not raw:
        return floor
    return max(raw, floor)


def _effective_start_date(configured: str | None, floor: str | None) -> str:
    """取 max(配置起点, 业务下界)；任一为空则取另一项。"""
    lo = (floor or "").strip()
    cfg = (configured or "").strip()
    if not lo:
        return cfg
    if not cfg:
        return lo
    return max(lo, cfg)


def _resolve_kline_micro_complete_end(
    local_kline_extract: KlineLocalExtract,
    open_trade_dates: list[str],
    calendar_end: str,
    period_count_rows: list[dict],
    count_field: str,
    *,
    label: str,
) -> str:
    """微观完整性检查截止日：当日宏观未达标则回退至最近达标开市日。"""
    complete_end = local_kline_extract.effective_complete_end_trade_date(
        open_trade_dates,
        calendar_end,
        period_count_rows,
        count_field,
    )
    if complete_end < calendar_end:
        print(
            f"[信息] 完整性检查截止 {complete_end}"
            f"（{calendar_end} {label}宏观数据未就绪，跳过）"
        )
    return complete_end


_KLINE_MACRO_DIMENSIONS: list[tuple[str, str]] = [
    ("kline_daily_count", "[宏观] 日线检查"),
    ("kline_adj_factor_count", "[宏观] 复权因子检查"),
    ("kline_stk_limit_count", "[宏观] 涨跌停检查"),
]


@dataclass(frozen=True)
class _KlineStrategySpec:
    """三维度共享 strategy 行为的参数化点。"""

    name: str                                  # daily / adj_factor / stk_limit
    label: str                                 # 日线 / 复权因子 / 涨跌停
    count_field: str                           # kline_daily_count / kline_adj_factor_count / kline_stk_limit_count
    desc_pull_by_date: str
    desc_check_complete: str
    info_complete_label: str                   # 区间内XX数据已完整 中的 XX
    range_data_key: str                        # KlineExtract 数据源链 key（按股区间）
    by_date_data_key: str                      # KlineExtract 数据源链 key（按交易日）
    workflow_pull_by_date: str
    workflow_check_complete: str
    local_filter_method: str                   # KlineLocalExtract.trade_date_filter_by_*
    local_period_count_method: str             # KlineLocalExtract.get_kline_*_period_count
    use_stk_limit_start: bool = False          # True: _resolve_stk_limit_start；False: kline_daily_start_date




_KLINE_STRATEGY_SPECS: dict[str, _KlineStrategySpec] = {
    "daily": _KlineStrategySpec(
        name="daily",
        label="日线",
        count_field="kline_daily_count",
        desc_pull_by_date="按日日线入库",
        desc_check_complete="[微观] 检查日线完整性",
        info_complete_label="日线",
        range_data_key="kline_daily",
        by_date_data_key="kline_daily_by_date",
        workflow_pull_by_date="pull_kline_daily_by_date",
        workflow_check_complete="check_kline_daily_complete_by_ts_code",
        local_filter_method="trade_date_filter_by_kline_count",
        local_period_count_method="get_kline_daily_period_count",
    ),
    "adj_factor": _KlineStrategySpec(
        name="adj_factor",
        label="复权因子",
        count_field="kline_adj_factor_count",
        desc_pull_by_date="按日复权因子入库",
        desc_check_complete="[微观] 检查复权因子完整性",
        info_complete_label="复权因子",
        range_data_key="kline_adj_factor",
        by_date_data_key="kline_adj_factor_by_date",
        workflow_pull_by_date="pull_kline_adj_factor_by_date",
        workflow_check_complete="check_kline_adj_factor_complete_by_ts_code",
        local_filter_method="trade_date_filter_by_adj_factor_count",
        local_period_count_method="get_kline_adj_factor_period_count",
    ),
    "stk_limit": _KlineStrategySpec(
        name="stk_limit",
        label="涨跌停",
        count_field="kline_stk_limit_count",
        desc_pull_by_date="按日涨跌停入库",
        desc_check_complete="[微观] 检查涨跌停完整性",
        info_complete_label="涨跌停",
        range_data_key="kline_stk_limit",
        by_date_data_key="kline_stk_limit_by_date",
        workflow_pull_by_date="pull_kline_stk_limit_by_date",
        workflow_check_complete="check_kline_stk_limit_complete_by_ts_code",
        local_filter_method="trade_date_filter_by_stk_limit_count",
        local_period_count_method="get_kline_stk_limit_period_count",
        use_stk_limit_start=True,
    ),
}


class KlineStrategy:
    def __init__(self):
        self.kline_workflow = KlineWorkflow()
        self.stock_base_service = StockBaseService()
        self.trade_cal_local = TradeCalLocalExtract()
        self.trade_cal_strategy = TradeCalStrategy()
        self.local_kline_extract = KlineLocalExtract()
        self.suspend_local = SuspendLocalExtract()
        self.kline_daily_start_date = settings.etl_start_date("kline_daily")
        self.kline_adj_factor_start_date = settings.etl_start_date(
            "kline_adj_factor", fallback_table="kline_daily"
        )
        self.kline_stk_limit_start_date = settings.etl_start_date("kline_stk_limit")

    # ---------- 起点解析 ----------

    def _resolve_stk_limit_start(self, start_date: str | None = None) -> str:
        """涨跌停拉取/校验起点：max(KLINE_STK_LIMIT_START_DATE, 入参, KLINE_DAILY_START_DATE)。"""
        return _effective_start_date(
            start_date or self.kline_daily_start_date,
            self.kline_stk_limit_start_date,
        )

    def _resolve_start(
        self, spec: _KlineStrategySpec, start_date: str | None
    ) -> str:
        if start_date is not None:
            if spec.use_stk_limit_start:
                return self._resolve_stk_limit_start(start_date)
            return start_date
        if spec.use_stk_limit_start:
            return self._resolve_stk_limit_start(None)
        if spec.name == "adj_factor":
            return self.kline_adj_factor_start_date
        return self.kline_daily_start_date

    # ---------- 内部统一实现 ----------

    def _resolve_spec(self, dimension: str) -> _KlineStrategySpec:
        spec = _KLINE_STRATEGY_SPECS.get(dimension)
        if spec is None:
            raise ValueError(f"未知 K 线维度: {dimension}")
        return spec

    def _finalize(self, spec: _KlineStrategySpec) -> int:
        return self.refresh_kline_macro_snapshot(
            label=spec.label, scan_dimensions=False
        )

    def _pull_by_date_range_loop(
        self,
        spec: _KlineStrategySpec,
        start_date: str | None,
        end_date: str | None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        """按交易日区间循环拉取全市场（三维度通用，95% 规则）。"""
        start = self._resolve_start(spec, start_date)
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        start = (start or "").strip()
        end = (end_date or "").strip()
        if not start or not end or start > end:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=start, end_date=end, exchange="SSE",
        )
        if progress_queue is not None:
            progress_queue.put({"log": f"刷新宏观快照 {start}~{end} ({spec.label})"})
        self.refresh_kline_macro_snapshot(
            start_date=start, end_date=end, label=spec.label
        )

        filter_method = getattr(self.local_kline_extract, spec.local_filter_method)
        trade_dates = sorted(filter_method(start_date=start, end_date=end))
        if not trade_dates:
            if progress_queue is not None:
                progress_queue.put({"log": f"{start}~{end} {spec.label} 已完整，无需补拉"})
            print(
                f"[信息] {start} ~ {end} 区间内{spec.info_complete_label}数据已完整"
                "（或 kline_daily_period_count 无缺失日）"
            )
            self._finalize(spec)
            return 0

        print(
            f"[信息] {spec.desc_pull_by_date}区间 {start}~{end}，"
            f"待补全开市日 {len(trade_dates)} 天"
            f"（首日 {trade_dates[0]}，末日 {trade_dates[-1]}）"
        )
        if progress_queue is not None:
            progress_queue.put({"log": f"{len(trade_dates)} 个开市日待补"})

        self.kline_workflow.kline_extract._get_source_chain(spec.by_date_data_key)

        workflow_method = getattr(self.kline_workflow, spec.workflow_pull_by_date)
        total_saved = 0
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": len(trade_dates)})
            for i, td in enumerate(trade_dates, 1):
                n = workflow_method(trade_date=td)
                total_saved += n
                progress_queue.put({
                    "index": i,
                    "total": len(trade_dates),
                    "period": td,
                    "saved": n,
                })
        else:
            pbar = tqdm_iter(trade_dates, desc=spec.desc_pull_by_date, unit="日")
            for td in pbar:
                n = workflow_method(trade_date=td)
                total_saved += n
                pbar.set_postfix(saved=n, total=total_saved, date=td)

        self._finalize(spec)
        return total_saved

    def _check_complete_history(
        self,
        spec: _KlineStrategySpec,
        *,
        refresh_snapshot: bool = True,
    ) -> int:
        """全 A 股逐只检查完整性（三维度通用）。

        refresh_snapshot=False 用于聚合路径，避免重复刷快照。
        """
        start = self._resolve_start(spec, None)
        start = (start or "").strip()
        end_today = datetime.now().strftime("%Y%m%d")
        if not start or start > end_today:
            return 0

        print(f"[微观] 开始检查{spec.label}完整性（逐股查漏补拉）...")
        self.trade_cal_strategy.ensure_trade_cal(
            start_date=start, end_date=end_today, exchange="SSE",
        )
        if refresh_snapshot:
            self.refresh_kline_macro_snapshot(
                start_date=start, end_date=end_today,
                label=spec.label, scan_dimensions=False,
            )

        open_trade_dates = self.trade_cal_local.get_open_trade_dates(
            start_date=start, end_date=end_today, exchange="SSE",
        )
        period_count_method = getattr(
            self.local_kline_extract, spec.local_period_count_method
        )
        complete_end = _resolve_kline_micro_complete_end(
            self.local_kline_extract,
            open_trade_dates,
            end_today,
            period_count_method(),
            spec.count_field,
            label=spec.label,
        )

        self.kline_workflow.kline_extract._get_source_chain(spec.range_data_key)

        # 一次性预加载全市场 (ts_code, trade_date)，消除逐股 DB 查询
        print(f"[微观] 预加载{spec.label}已入库 trade_date（{spec.name}）...")
        t0 = time.monotonic()
        resolved_by_code = self.kline_workflow.preload_resolved_trade_dates(
            spec.name, start_date=start, end_date=complete_end,
        )
        print(
            f"[微观] {spec.label}预加载完成：{len(resolved_by_code)} 股，"
            f"耗时 {time.monotonic() - t0:.1f}s"
        )

        # 一次性预加载全市场全天停牌日，从 expected 中扣除，避免误判缺日
        print(f"[微观] 预加载全天停牌日 {start}~{complete_end} ...")
        t0 = time.monotonic()
        suspend_dates_by_code = self.suspend_local.preload_full_day_suspend_dates(
            start_date=start, end_date=complete_end,
        )
        print(
            f"[微观] 全天停牌预加载完成：{len(suspend_dates_by_code)} 股，"
            f"耗时 {time.monotonic() - t0:.1f}s"
        )

        check_method = getattr(self.kline_workflow, spec.workflow_check_complete)
        stock_list = self.stock_base_service.get_all_stock_list_a()
        missing_all: list[str] = []
        passed_stocks = 0
        failed_stocks = 0
        active_stocks = len(stock_list)

        def _set_postfix(pbar) -> None:
            pbar.set_postfix(
                **format_micro_stock_postfix(
                    active_stocks=active_stocks,
                    passed_stocks=passed_stocks,
                    failed_stocks=failed_stocks,
                    missing_items=len(missing_all),
                )
            )

        pbar = tqdm_iter(stock_list, desc=spec.desc_check_complete, unit="股票")
        for inst in pbar:
            ts_code = getattr(inst, "ts_code", None)
            if not ts_code:
                _set_postfix(pbar)
                continue

            list_date = getattr(inst, "list_date", None)
            delist_date = getattr(inst, "delist_date", None)
            stock_start = _effective_list_date(list_date, start)
            if not stock_start:
                _set_postfix(pbar)
                continue

            d = str(delist_date).strip() if delist_date else ""
            stock_end = min(complete_end, d) if d else complete_end
            if stock_start > stock_end:
                passed_stocks += 1
                _set_postfix(pbar)
                continue

            resolved = resolved_by_code.get(str(ts_code).strip(), [])
            suspend_dates = suspend_dates_by_code.get(str(ts_code).strip(), set())

            missing_dates = check_method(
                ts_code=ts_code,
                list_date=list_date,
                delist_date=delist_date,
                start_date=stock_start,
                end_date=stock_end,
                open_trade_dates=open_trade_dates,
                resolved_trade_dates=resolved,
                full_day_suspend_dates=suspend_dates,
            )
            if missing_dates:
                failed_stocks += 1
            else:
                passed_stocks += 1
            missing_all.extend(f"{ts_code},{td}" for td in missing_dates)
            _set_postfix(pbar)

        if refresh_snapshot:
            self.refresh_kline_macro_snapshot(
                start_date=start, end_date=end_today,
                label=spec.label, scan_dimensions=False,
            )
        n = len(missing_all)
        print(
            f"[微观] {spec.label}检查完成：活跃{active_stocks}股 "
            f"通过{passed_stocks}股 缺失{failed_stocks}股 缺日{n}条"
        )
        return n

    # ---------- 公开 API：按日（单日 / 区间 / 单日+finalize） ----------

    def pull_kline_daily_by_date(self, trade_date: str) -> int:
        """按单日拉取全市场日线（不刷宏观快照，供 date_range 循环复用）。"""
        return self.kline_workflow.pull_kline_daily_by_date(trade_date=trade_date)

    def pull_kline_adj_factor_by_date(self, trade_date: str) -> int:
        """按单日拉取全市场复权因子。"""
        return self.kline_workflow.pull_kline_adj_factor_by_date(trade_date=trade_date)

    def pull_kline_stk_limit_by_date(self, trade_date: str) -> int:
        """按单日拉取全市场涨跌停价。"""
        return self.kline_workflow.pull_kline_stk_limit_by_date(trade_date=trade_date)

    def pull_kline_daily_by_date_with_finalize(self, trade_date: str) -> int:
        """按单日拉日线并刷新宏观快照。"""
        total = self.pull_kline_daily_by_date(trade_date)
        self.finalize_kline_daily_after_update()
        return total

    def pull_kline_adj_factor_by_date_with_finalize(self, trade_date: str) -> int:
        """按单日拉复权因子并刷新宏观快照。"""
        total = self.pull_kline_adj_factor_by_date(trade_date)
        self.finalize_kline_adj_factor_after_update()
        return total

    def pull_kline_stk_limit_by_date_with_finalize(self, trade_date: str) -> int:
        """按单日拉涨跌停并刷新宏观快照。"""
        total = self.pull_kline_stk_limit_by_date(trade_date)
        self.finalize_kline_stk_limit_after_update()
        return total

    def pull_kline_daily_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        """按交易日区间增量拉取全市场日线（95% 规则）。"""
        return self._pull_by_date_range_loop(
            self._resolve_spec("daily"), start_date, end_date,
            progress_queue=progress_queue,
        )

    def pull_kline_adj_factor_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        """按交易日区间增量拉取全市场复权因子（95% 规则）。"""
        return self._pull_by_date_range_loop(
            self._resolve_spec("adj_factor"), start_date, end_date,
            progress_queue=progress_queue,
        )

    def pull_kline_stk_limit_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        """按交易日区间增量拉取全市场涨跌停价（95% 规则）。"""
        return self._pull_by_date_range_loop(
            self._resolve_spec("stk_limit"), start_date, end_date,
            progress_queue=progress_queue,
        )

    # ---------- 公开 API：完整性校验 ----------

    def check_kline_daily_complete_history(self) -> int:
        """全 A 股逐只检查日线完整性，缺日写 log 并按区间补拉。"""
        return self._check_complete_history(self._resolve_spec("daily"))

    def check_kline_adj_factor_complete_history(self) -> int:
        """全 A 股逐只检查复权因子完整性，缺日写 log 并按区间补拉。"""
        return self._check_complete_history(self._resolve_spec("adj_factor"))

    def check_kline_stk_limit_complete_history(self) -> int:
        """全 A 股逐只检查涨跌停价完整性，缺日写 log 并按区间补拉。"""
        return self._check_complete_history(self._resolve_spec("stk_limit"))

    def check_kline_complete_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """完整性检查：传 start/end 时按窗口宏观补拉；否则全历史微观扫描。"""
        start = (start_date or "").strip() if start_date else ""
        end = (end_date or "").strip() if end_date else ""
        if start or end:
            if not start:
                start = self.kline_daily_start_date
            if not end:
                end = datetime.now().strftime("%Y%m%d")
            if not start or start > end:
                return 0
            print(f"[宏观] K 线窗口完整性检查 {start}~{end}（按日 pull + 95% 守门）")
            total = 0
            total += self.pull_kline_daily_by_date_range(start, end)
            total += self.pull_kline_adj_factor_by_date_range(start, end)
            total += self.pull_kline_stk_limit_by_date_range(start, end)
            print(f"[宏观] K 线窗口检查完成，累计写入 {total} 条")
            return total

        print("[微观] 开始 K 线全维度完整性检查（日线 + 复权 + 涨跌停）...")
        self.refresh_kline_macro_snapshot(scan_dimensions=True)
        total = 0
        for dimension in ("daily", "adj_factor", "stk_limit"):
            total += self._check_complete_history(
                self._resolve_spec(dimension), refresh_snapshot=False,
            )
        self.refresh_kline_macro_snapshot(scan_dimensions=False)
        print(f"[微观] K 线全维度检查完成，累计缺日 {total} 条")
        return total

    # ---------- 公开 API：宏观快照 / finalize ----------

    def kline_daily_period_count(
        self, start_date: str | None = None, end_date: str | None = None,
    ) -> int:
        """更新 kline_daily_period_count 快照。"""
        if start_date is None:
            start_date = self.kline_daily_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not start or not end or start > end:
            return 0
        self.trade_cal_strategy.ensure_trade_cal(
            start_date=start, end_date=end, exchange="SSE",
        )
        return self.kline_workflow.kline_daily_period_count(
            start_date=start, end_date=end,
        )

    def refresh_kline_macro_snapshot(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        label: str = "日K",
        scan_dimensions: bool = True,
    ) -> int:
        """刷新 kline_daily_period_count 宏观快照：可选三维度 tqdm + 落库。"""
        if start_date is None:
            start_date = self.kline_daily_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not start or not end or start > end:
            return 0
        print(f"[宏观] 刷新{label}完整性快照 {start}~{end} ...")
        t0 = time.monotonic()
        self.trade_cal_strategy.ensure_trade_cal(
            start_date=start, end_date=end, exchange="SSE",
        )
        merged = self.kline_workflow.build_kline_daily_period_count_rows(
            start_date=start, end_date=end,
        )
        if not merged:
            print("[宏观] 无开市日数据，跳过")
            return 0
        if scan_dimensions:
            for count_field, desc in _KLINE_MACRO_DIMENSIONS:
                stats = scan_macro_snapshot_rows(
                    merged, count_field=count_field, desc=desc, unit="日",
                )
                print(
                    f"[宏观] {desc}完成：活跃{stats['active_stock']}股 "
                    f"通过{stats['pass_days']}日 缺失{stats['fail_days']}日 "
                    f"缺条{stats['missing_records']}"
                )
        n = self.kline_workflow.load_kline_daily_period_count_rows(merged)
        elapsed = time.monotonic() - t0
        suffix = "" if scan_dimensions else "（无维度扫描）"
        print(f"[宏观] 快照落库 {n} 条{suffix}，耗时 {elapsed:.1f}s")
        return n

    def finalize_kline_daily_after_update(self) -> int:
        """入库后：仅刷新宏观快照（无维度 tqdm）。"""
        return self._finalize(self._resolve_spec("daily"))

    def finalize_kline_adj_factor_after_update(self) -> int:
        """入库后：仅刷新宏观快照（无维度 tqdm）。"""
        return self._finalize(self._resolve_spec("adj_factor"))

    def finalize_kline_stk_limit_after_update(self) -> int:
        """入库后：仅刷新宏观快照（无维度 tqdm）。"""
        return self._finalize(self._resolve_spec("stk_limit"))
