from typing import Any, Dict, List, Optional

from src.service.financial.financial_report_service import ReportService

_COUNT_KEY_BY_REPORT_TYPE: Dict[str, str] = {
    "income": "report_income_count",
    "balance": "report_balance_count",
    "cashflow": "report_cashflow_count",
    "indicator": "report_indicator_count",
}


class ReportExtract:
    def __init__(self):
        self._report_service = ReportService()

    def get_report_period_list(
        self,
        *,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        调用 service 层 ReportService 的 get_period_list 方法获取报告期列表。

        Args:
            start_period_date: 报告期下界（含），YYYYMMDD；不传则不限制。
            end_period_date: 报告期上界（含），YYYYMMDD；不传则不限制。

        Returns:
            合并后的报告期列表；每项含 report_period 及三张表各自的条数统计。
        """
        return self._report_service.get_period_list(
            start_period_date=start_period_date,
            end_period_date=end_period_date,
        )

    def get_report_period_count(self) -> List[Dict[str, Any]]:
        """
        从库表 report_period_count 拉取全量快照（无筛选）。

        Returns:
            每项含 report_period、period_stock_count 及三张表条数统计等。
        """
        return self._report_service.list_report_period_count()

    def list_periods_below_threshold(
        self,
        *,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
        report_type: str,
    ) -> List[str]:
        """
        返回指定报表类型「条数未达 period_stock_count × 95%」的报告期列表（按报告期新→旧）。

        args:
            start_period_date: 报告期下界（含），YYYYMMDD；不传则不限制。
            end_period_date: 报告期上界（含），YYYYMMDD；不传则不限制。
            report_type: 报表类型，可选值为 "income", "balance", "cashflow"。
        逻辑：
            1. 读 report_period_count 全量快照；
            2. 对应表条数 < period_stock_count × 0.95 视为缺；
            3. 按 [start_period_date, end_period_date] 字典序截取（任一侧不传则不裁该侧）；
            4. 去重后按报告期新到旧返回。
        """
        count_key = _COUNT_KEY_BY_REPORT_TYPE.get(report_type)
        if count_key is None:
            raise ValueError(
                "report_type 须为 income、balance、cashflow、indicator 之一，"
                f"收到: {report_type!r}"
            )
        
        # step1:通过get_report_period_count获取report_period_count表全部记录，返回列表，每项含 report_period、period_stock_count 及三张表条数统计等。
        rows = self.get_report_period_count()
        # step2:根据report_type,比对对应报表类型的条数统计和股票在市数量period_stock_count，如果小于period_stock_count的95%，则认为该报告期财报数据缺失。
        # 2005 年前只校验半年报（0630）和年报（1231），季报（0331/0930）直接跳过。
        threshold = 0.95
        period_list_missing: List[str] = []
        for row in rows:
            period = row.get("report_period")
            if not period:
                continue
            # 2005 年前只校验半年报和年报
            year = int(period[:4])
            if year < 2005 and period[4:] not in ("0630", "1231"):
                continue
            stock_n = row.get("period_stock_count")
            if stock_n is None or stock_n <= 0:
                continue
            cnt = row.get(count_key)
            if cnt is None:
                cnt = 0
            if cnt < threshold * stock_n:
                period_list_missing.append(period)

        # step3: 此时 period_list_missing 已是「判定为数据不足的报告期」；若未限定日期区间则直接返回
        if start_period_date is None and end_period_date is None:
            return sorted(set(period_list_missing), reverse=True)

        # step4/step5：按起止边界（含）筛缺失期；某一侧不传则跳过该侧的判定。
        filtered: List[str] = []
        for p in period_list_missing:
            if start_period_date is not None and p < start_period_date:
                continue
            if end_period_date is not None and p > end_period_date:
                continue
            filtered.append(p)
        return sorted(set(filtered), reverse=True)

    def get_report_rows_by_end_date(
        self, report_type: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        按报告期读取库内已有财报行（经 Service → Model）。

        Args:
            report_type: income / balance / cashflow
            end_date: 报告期 YYYYMMDD
        """
        return self._report_service.list_by_end_date(report_type, end_date)