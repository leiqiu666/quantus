from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.common.database import Database
from src.entities.data_entities.financial.financial_report_period_count_entities import ReportPeriodCountEntities


class ReportPeriodCountModel:
    def __init__(self) -> None:
        self.db = Database()

    def get_stock_counts_by_range(
        self,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        按报告期区间查询 report_period -> period_stock_count 映射。

        Args:
            start_period_date: 报告期下界（含），YYYYMMDD；不传则不限制。
            end_period_date: 报告期上界（含），YYYYMMDD；不传则不限制。
        """
        session: Session = self.db.get_session()
        try:
            query = session.query(ReportPeriodCountEntities)
            if start_period_date is not None:
                query = query.filter(
                    ReportPeriodCountEntities.report_period >= start_period_date
                )
            if end_period_date is not None:
                query = query.filter(
                    ReportPeriodCountEntities.report_period <= end_period_date
                )
            rows = query.all()
            return {r.report_period: int(r.period_stock_count) for r in rows}
        finally:
            session.close()

    def list_all(self) -> List[Dict[str, Any]]:
        """
        查询 report_period_count 全表记录（无筛选条件）。
        列表按 report_period 倒序（新到旧）。

        Returns:
            字典列表，每项含 id、report_period、period_stock_count 及三张表条数字段。
        """
        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(ReportPeriodCountEntities)
                .order_by(ReportPeriodCountEntities.report_period.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "report_period": r.report_period,
                    "period_stock_count": r.period_stock_count,
                    "report_income_count": r.report_income_count,
                    "report_balance_count": r.report_balance_count,
                    "report_cashflow_count": r.report_cashflow_count,
                    "report_indicator_count": r.report_indicator_count,
                }
                for r in rows
            ]
        finally:
            session.close()


if __name__ == "__main__":
    m = ReportPeriodCountModel()
    print(len(m.list_all()))
