from typing import Any, Dict, List, Optional

from sqlalchemy import func

from src.common.database import Database
from src.entities.data_entities.financial.financial_report_indicator_entities import ReportIndicatorEntities


class ReportIndicatorModel:
    def __init__(self):
        self.db = Database()

    def get_period_list(
        self,
        *,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取财务指标报告期列表。
        按 end_date 分组统计条数，可按区间筛选。
        返回按 report_period 倒序的列表，元素含 report_period、report_indicator_count。
        """
        clauses = [
            ReportIndicatorEntities.end_date.isnot(None),
            ReportIndicatorEntities.end_date != "",
        ]
        if start_period_date is not None:
            clauses.append(ReportIndicatorEntities.end_date >= start_period_date)
        if end_period_date is not None:
            clauses.append(ReportIndicatorEntities.end_date <= end_period_date)
        rows = self.db.select_grouped(
            ReportIndicatorEntities,
            ReportIndicatorEntities.end_date,
            func.count(ReportIndicatorEntities.id),
            group_by=(ReportIndicatorEntities.end_date,),
            order_by=(ReportIndicatorEntities.end_date.desc(),),
            where_clauses=tuple(clauses),
        )
        return [
            {"report_period": end_date, "report_indicator_count": int(cnt)}
            for end_date, cnt in rows
        ]

    def get_report_indicator_by_ts_code(self, ts_code: str, **kwargs):
        """根据股票代码获取财务指标数据（ORM 实例列表）。"""
        return self.db.get_all(ReportIndicatorEntities, ts_code=ts_code, **kwargs)

    def get_report_indicator_all(self, *, return_fields: tuple[str, ...] | None = None, **kwargs):
        """
        获取财务指标全量数据。
        return_fields 为 None 时返回 ORM 实例列表；否则返回指定列的元组列表。
        """
        if return_fields is None:
            return self.db.get_all(ReportIndicatorEntities, **kwargs)
        if not return_fields:
            raise ValueError("return_fields 不能为空元组")
        return self.db.fetch_model_columns(ReportIndicatorEntities, return_fields, **kwargs)

    def list_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """返回指定报告期全行（dict 列表，供 Load filter 比对）。"""
        rows = self.db.get_all(ReportIndicatorEntities, end_date=str(end_date).strip())
        columns = ReportIndicatorEntities.__table__.columns
        return [
            {col.name: getattr(row, col.name) for col in columns}
            for row in rows
        ]


if __name__ == "__main__":
    m = ReportIndicatorModel()
    print(m.get_period_list())
