from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Type

from tqdm import tqdm

from src.common.function import report_period_generate, tqdm_iter
from src.etl.extract.financial.financial_report_extract import ReportExtract
from src.etl.extract.local.financial.financial_report_local_extract import ReportExtract as LocalReportExtract
from src.etl.extract.local.stock.stock_local_extract import StockExtract as LocalStockExtract
from src.etl.transform.financial.financial_report_transform import ReportTransform
from src.etl.load.financial.financial_report_load import ReportLoad
from src.entities.data_entities.financial.financial_report_income_entities import ReportIncomeEntities
from src.entities.data_entities.financial.financial_report_balance_entities import ReportBalanceEntities
from src.entities.data_entities.financial.financial_report_cashflow_entities import ReportCashflowEntities
from src.entities.data_entities.financial.financial_report_indicator_entities import ReportIndicatorEntities

from src.model.financial.financial_report_income_model import ReportIncomeModel
from src.model.financial.financial_report_balance_model import ReportBalanceModel
from src.model.financial.financial_report_cashflow_model import ReportCashflowModel
from src.model.financial.financial_report_indicator_model import ReportIndicatorModel
from src.service.stock.stock_active_count_service import StockActiveCountService
from src.service.stock.stock_base_service import StockBaseService
from src.etl.log.missing_log import MissingLog


@dataclass(frozen=True)
class _ReportSpec:
    """三表 pipeline 的差异点。Extract/Client 已按 report_type 自分派，这里无需 pull lambda。"""
    report_type: str           # "income" | "balance" | "cashflow"
    entity: Type[Any]          # ReportIncomeEntities / ...
    missing_entity: str        # "financial_report_income" | "financial_report_balance" | "financial_report_cashflow"
    label: str                 # "利润表" / ...
    query_by_code: Callable[["ReportWorkflow", str], list]
    query_all: Callable[["ReportWorkflow", tuple[str, ...]], list]


_REPORT_SPECS: dict[str, _ReportSpec] = {
    "income": _ReportSpec(
        report_type="income",
        entity=ReportIncomeEntities,
        missing_entity="financial_report_income",
        label="利润表",
        query_by_code=lambda wf, ts_code: wf.report_income_model.get_report_income_by_ts_code(ts_code=ts_code),
        query_all=lambda wf, fields: wf.report_income_model.get_report_income_all(return_fields=fields),
    ),
    "balance": _ReportSpec(
        report_type="balance",
        entity=ReportBalanceEntities,
        missing_entity="financial_report_balance",
        label="资产负债表",
        query_by_code=lambda wf, ts_code: wf.report_balance_model.get_report_balance_by_ts_code(ts_code=ts_code),
        query_all=lambda wf, fields: wf.report_balance_model.get_report_balance_all(return_fields=fields),
    ),
    "cashflow": _ReportSpec(
        report_type="cashflow",
        entity=ReportCashflowEntities,
        missing_entity="financial_report_cashflow",
        label="现金流量表",
        query_by_code=lambda wf, ts_code: wf.report_cashflow_model.get_report_cashflow_by_ts_code(ts_code=ts_code),
        query_all=lambda wf, fields: wf.report_cashflow_model.get_report_cashflow_all(return_fields=fields),
    ),
    "indicator": _ReportSpec(
        report_type="indicator",
        entity=ReportIndicatorEntities,
        missing_entity="financial_report_indicator",
        label="财务指标",
        query_by_code=lambda wf, ts_code: wf.report_indicator_model.get_report_indicator_by_ts_code(ts_code=ts_code),
        query_all=lambda wf, fields: wf.report_indicator_model.get_report_indicator_all(return_fields=fields),
    ),
}

_REPORT_MISSING_ENTITIES = frozenset(spec.missing_entity for spec in _REPORT_SPECS.values())
_SPEC_BY_MISSING_ENTITY = {spec.missing_entity: spec for spec in _REPORT_SPECS.values()}


def _resolve_spec(*, report_type: str | None = None, missing_entity: str | None = None) -> _ReportSpec:
    if report_type is not None:
        spec = _REPORT_SPECS.get(report_type)
        if spec is None:
            raise ValueError(f"report_type 须为 {tuple(_REPORT_SPECS)} 之一，收到: {report_type!r}")
        return spec
    if missing_entity is not None:
        spec = _SPEC_BY_MISSING_ENTITY.get(missing_entity)
        if spec is None:
            raise ValueError(
                f"missing_entity 须为 {_REPORT_MISSING_ENTITIES} 之一，收到: {missing_entity!r}"
            )
        return spec
    raise TypeError("_resolve_spec 须传 report_type 或 missing_entity")


class ReportWorkflow:
    def __init__(self):
        self.report_extract = ReportExtract()
        self.local_report_extract = LocalReportExtract()
        self.local_stock_extract = LocalStockExtract()
        self.report_transform = ReportTransform()
        self.active_count_service = StockActiveCountService()
        self.report_load = ReportLoad()
        self.report_income_model = ReportIncomeModel()
        self.report_balance_model = ReportBalanceModel()
        self.report_cashflow_model = ReportCashflowModel()
        self.report_indicator_model = ReportIndicatorModel()
        self.stock_base_service = StockBaseService()
        self.missing_log = MissingLog()

    def report_by_period(self, report_type: str, period: str) -> int:
        """按报告期批量入库单张财报表（用于历史数据初始化）。"""
        spec = _resolve_spec(report_type=report_type)
        df = self.report_extract.pull(report_type, period=period)
        df = self.report_transform.filter_report_by_delist(
            period, df, stock_extract=self.local_stock_extract
        )
        df = self.report_transform.report_transform_merge_now(df)
        df = self.report_transform.report_more_detail_to_json(spec.entity, df)
        load_result = self.report_load.load_report_filter(
            entities=spec.entity,
            df=df,
            scope_end_date=period,
            local_report_extract=self.local_report_extract,
        )
        return load_result.total_written

    def report_by_ts_code(self, report_type: str, ts_code: str, end_date: str) -> int:
        """按个股+报告期补单条数据（用于缺失数据补录）。"""
        spec = _resolve_spec(report_type=report_type)
        df = self.report_extract.pull_by_code(report_type, ts_code, end_date=end_date)
        df = self.report_transform.report_transform_merge_now(df)
        df = self.report_transform.report_more_detail_to_json(spec.entity, df)
        load_result = self.report_load.load_report_filter(
            entities=spec.entity,
            df=df,
            scope_end_date=end_date,
            local_report_extract=self.local_report_extract,
        )
        return load_result.total_written

    def check_report_complete(
        self,
        missing_entity: str,
        start_end_date: str | None = None,
        end_end_date: str | None = None,
    ) -> list[str]:
        """
        按 missing_entity 检查全 A 股在区间内的财报报告期是否齐全；缺期写 log 并按个股+期补拉。

        Args:
            missing_entity: report_income / report_balance / report_cashflow。
            start_end_date: 检查起点（YYYYMMDD），默认 max(20050101, list_date)。
            end_end_date: 检查终点（YYYYMMDD），默认今日。

        Returns:
            缺期条目（"ts_code,end_date" 字符串）的扁平列表。
        """
        spec = _resolve_spec(missing_entity=missing_entity)
        if end_end_date is None:
            end_end_date = datetime.now().strftime("%Y%m%d")

        # 一次性预加载该表所有 (ts_code, end_date)，避免逐股查库
        all_rows = spec.query_all(self, ("ts_code", "end_date"))
        stock_to_periods: dict[str, set[str]] = defaultdict(set)
        for row in all_rows:
            stock_cell, end_cell = row[0], row[1]
            if stock_cell is None or end_cell is None:
                continue
            stock_key = str(stock_cell).strip()
            end_key = str(end_cell).strip()
            if stock_key and end_key:
                stock_to_periods[stock_key].add(end_key)

        stock_list = self.stock_base_service.get_all_stock_list_a()
        missing_flat: list[str] = []
        vip_pulled_periods: set[str] = set()
        pbar = tqdm_iter(stock_list, desc=f"检查{spec.label}完整性", unit="股票")
        for stock_row in pbar:
            stock_code = str(getattr(stock_row, "ts_code", None) or "").strip()
            if not stock_code:
                continue
            list_date = getattr(stock_row, "list_date", None) or "20050101"
            range_start = max(start_end_date or "20050101", list_date)

            known = sorted(stock_to_periods.get(stock_code, set()))
            missing_periods = self.report_transform.check_report_complete_by_end_dates(
                end_dates=known,
                start_end_date=range_start,
                end_end_date=end_end_date,
            )
            self._handle_missing_periods(
                spec, stock_code, missing_periods, verbose=True,
                vip_pulled_periods=vip_pulled_periods,
            )
            missing_flat.extend(f"{stock_code},{ed}" for ed in missing_periods)
            pbar.set_postfix(saved=len(missing_periods))

        return missing_flat

    def check_report_complete_by_ts_code(
        self,
        ts_code: str,
        missing_entity: str,
        start_end_date: str | None = None,
        end_end_date: str | None = None,
        *,
        end_dates: list[str] | None = None,
        vip_pulled_periods: set[str] | None = None,
    ) -> list[str]:
        """
        按 missing_entity 检查单只股票在区间内的财报报告期是否齐全，并尝试补拉缺失期次。

        CLI ``report check-report-complete`` 使用本方法（逐股查库）。
        批量预加载全表路径见 ``check_report_complete``。
        """
        spec = _resolve_spec(missing_entity=missing_entity)
        if end_end_date is None:
            end_end_date = datetime.now().strftime("%Y%m%d")
        if start_end_date is None:
            start_end_date = "19900101"

        if end_dates is None:
            rows = spec.query_by_code(self, ts_code)
            resolved_end_dates = [r.end_date for r in rows]
        else:
            resolved_end_dates = list(end_dates)

        missing_periods = self.report_transform.check_report_complete_by_end_dates(
            end_dates=resolved_end_dates,
            start_end_date=start_end_date,
            end_end_date=end_end_date,
        )
        self._handle_missing_periods(
            spec, ts_code, missing_periods, verbose=False,
            vip_pulled_periods=vip_pulled_periods,
        )
        return missing_periods

    def _handle_missing_periods(
        self,
        spec: _ReportSpec,
        ts_code: str,
        missing_periods: list[str],
        *,
        verbose: bool,
        vip_pulled_periods: set[str] | None = None,
    ) -> None:
        """写缺期初始 log → 按报告期 VIP 补拉 → 终态合并。"""
        if not missing_periods:
            return
        self.missing_log.upsert_missing_logs(
            missing_items=[f"{ts_code},{ed}" for ed in missing_periods],
            missing_entity=spec.missing_entity,
        )

        succeeded: list[str] = []
        failed: list[str] = []
        for period in missing_periods:
            if vip_pulled_periods is not None:
                if period in vip_pulled_periods:
                    rows = spec.query_by_code(self, ts_code)
                    resolved = {str(r.end_date).strip() for r in rows}
                    if period in resolved:
                        succeeded.append(period)
                    else:
                        failed.append(period)
                    continue
                vip_pulled_periods.add(period)
                if verbose:
                    tqdm.write(f"VIP 拉取{spec.label}: {period}")
                self.report_by_period(spec.report_type, period)
                rows = spec.query_by_code(self, ts_code)
                resolved = {str(r.end_date).strip() for r in rows}
                if period in resolved:
                    succeeded.append(period)
                else:
                    failed.append(period)
                continue

            if verbose:
                tqdm.write(f"VIP 拉取{spec.label}: {ts_code} {period}")
            saved = self.report_by_period(spec.report_type, period)
            rows = spec.query_by_code(self, ts_code)
            resolved = {str(r.end_date).strip() for r in rows}
            if period in resolved or saved > 0:
                succeeded.append(period)
            else:
                failed.append(period)

        if succeeded:
            self.missing_log.delete_missing_logs(
                missing_items=[f"{ts_code},{ed}" for ed in succeeded],
                missing_entity=spec.missing_entity,
            )
        if failed:
            self.missing_log.upsert_missing_logs(
                missing_items=[f"{ts_code},{ed}" for ed in failed],
                missing_entity=spec.missing_entity,
            )

    def build_report_period_count_rows(
        self, start_date: str, end_date: str
    ) -> list[dict[str, int | str]]:
        """聚合 report_period_count 行（不落库）。"""
        if not start_date or not end_date or start_date > end_date:
            return []

        period_report_rows = self.local_report_extract.get_report_period_list(
            start_period_date=start_date,
            end_period_date=end_date,
        )
        report_by_period = {r["report_period"]: r for r in period_report_rows}
        periods = report_period_generate(start_date, end_date)
        stock_counts = self.active_count_service.resolve_listed_counts(periods)

        merged: list[dict[str, int | str]] = []
        for period in periods:
            pr = report_by_period.get(period, {})
            merged.append(
                {
                    "report_period": period,
                    "period_stock_count": int(stock_counts.get(period, 0)),
                    "report_income_count": int(pr.get("report_income_count") or 0),
                    "report_balance_count": int(pr.get("report_balance_count") or 0),
                    "report_cashflow_count": int(pr.get("report_cashflow_count") or 0),
                    "report_indicator_count": int(pr.get("report_indicator_count") or 0),
                }
            )
        return merged

    def report_period_count(self, start_date: str, end_date: str) -> int:
        """聚合 + 落库 report_period_count 快照。"""
        merged = self.build_report_period_count_rows(start_date, end_date)
        if not merged:
            return 0
        return self.report_load.load_report_period_count(merged)

    def load_report_period_count_rows(
        self, merged: list[dict[str, int | str]]
    ) -> int:
        """将已聚合的 report_period_count 行 upsert 落库。"""
        if not merged:
            return 0
        return self.report_load.load_report_period_count(merged)
