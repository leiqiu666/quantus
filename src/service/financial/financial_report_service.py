from typing import Any, Dict, List, Optional

from src.model.financial.financial_report_balance_model import ReportBalanceModel
from src.model.financial.financial_report_cashflow_model import ReportCashflowModel
from src.model.financial.financial_report_income_model import ReportIncomeModel
from src.model.financial.financial_report_indicator_model import ReportIndicatorModel
from src.model.financial.financial_report_period_count_model import ReportPeriodCountModel
from src.service.stock.stock_active_count_service import StockActiveCountService


class ReportService:
    def __init__(self):
        self._income_model = ReportIncomeModel()
        self._balance_model = ReportBalanceModel()
        self._cashflow_model = ReportCashflowModel()
        self._indicator_model = ReportIndicatorModel()
        self._period_count_model = ReportPeriodCountModel()
        self._active_count_service = StockActiveCountService()

    def list_report_period_count(self) -> List[Dict[str, Any]]:
        """查询 report_period_count 表全部记录（无参数）。"""
        return self._period_count_model.list_all()

    def get_period_list(
        self,
        *,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        合并利润表、资产负债表、现金流量表、财务指标四个 model 的 get_period_list 结果。
        同一 report_period 只保留一行，内含四张表各自的条数统计；某表缺少该报告期时对应 count 为 0。
        列表按 report_period 倒序（新到旧）。

        Args:
            start_period_date: 报告期下界（含），YYYYMMDD；不传则不限制。
            end_period_date: 报告期上界（含），YYYYMMDD；不传则不限制。
        """
        income_rows = self._income_model.get_period_list(
            start_period_date=start_period_date,
            end_period_date=end_period_date,
        )
        balance_rows = self._balance_model.get_period_list(
            start_period_date=start_period_date,
            end_period_date=end_period_date,
        )
        cashflow_rows = self._cashflow_model.get_period_list(
            start_period_date=start_period_date,
            end_period_date=end_period_date,
        )
        indicator_rows = self._indicator_model.get_period_list(
            start_period_date=start_period_date,
            end_period_date=end_period_date,
        )

        merged: Dict[str, Dict[str, Any]] = {}
        for row in income_rows + balance_rows + cashflow_rows + indicator_rows:
            period = row["report_period"]
            if period not in merged:
                merged[period] = {
                    "report_period": period,
                    "period_stock_count": 0,
                    "report_income_count": 0,
                    "report_balance_count": 0,
                    "report_cashflow_count": 0,
                    "report_indicator_count": 0,
                }
            for key, value in row.items():
                if key != "report_period":
                    merged[period][key] = value

        stock_counts = self._active_count_service.resolve_listed_counts(
            list(merged.keys())
        )
        for period, row in merged.items():
            row["period_stock_count"] = stock_counts.get(
                period,
                0,
            )

        result = list(merged.values())
        result.sort(key=lambda x: x["report_period"], reverse=True)
        return result

    def list_income_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """指定报告期利润表全行。"""
        return self._income_model.list_by_end_date(end_date)

    def list_balance_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """指定报告期资产负债表全行。"""
        return self._balance_model.list_by_end_date(end_date)

    def list_cashflow_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """指定报告期现金流量表全行。"""
        return self._cashflow_model.list_by_end_date(end_date)

    def list_indicator_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """指定报告期财务指标全行。"""
        return self._indicator_model.list_by_end_date(end_date)

    def list_by_end_date(self, report_type: str, end_date: str) -> List[Dict[str, Any]]:
        """按报表类型返回指定报告期全行。"""
        if report_type == "income":
            return self.list_income_by_end_date(end_date)
        if report_type == "balance":
            return self.list_balance_by_end_date(end_date)
        if report_type == "cashflow":
            return self.list_cashflow_by_end_date(end_date)
        if report_type == "indicator":
            return self.list_indicator_by_end_date(end_date)
        raise ValueError(
            "report_type 须为 income、balance、cashflow、indicator 之一，"
            f"收到: {report_type!r}"
        )


if __name__ == "__main__":
    report_service = ReportService()
    print(report_service.get_period_list(start_period_date="20200101", end_period_date="20201231"))