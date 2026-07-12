from typing import Any, Dict, List, Optional

from sqlalchemy import func

from src.common.database import Database
from src.entities.data_entities.financial.financial_report_cashflow_entities import ReportCashflowEntities


class ReportCashflowModel:
    def __init__(self):
        self.db = Database()

    def get_period_list(
        self,
        *,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取现金流量表报告期列表
        Args:
            start_period_date: 报告期下界（含），YYYYMMDD；与表字段 end_date 区分命名
            end_period_date: 报告期上界（含），YYYYMMDD
        逻辑:
            1. report_cashflow 表中 end_date 为报告期
            2. 按 end_date 分组统计条数，可按起止报告期筛选
        Returns:
            报告期列表（倒序），元素含 report_period、report_cashflow_count
        """
        clauses = [
            ReportCashflowEntities.end_date.isnot(None),
            ReportCashflowEntities.end_date != "",
        ]
        if start_period_date is not None:
            clauses.append(ReportCashflowEntities.end_date >= start_period_date)
        if end_period_date is not None:
            clauses.append(ReportCashflowEntities.end_date <= end_period_date)
        rows = self.db.select_grouped(
            ReportCashflowEntities,
            ReportCashflowEntities.end_date,
            func.count(ReportCashflowEntities.id),
            group_by=(ReportCashflowEntities.end_date,),
            order_by=(ReportCashflowEntities.end_date.desc(),),
            where_clauses=tuple(clauses),
        )
        return [
            {"report_period": end_date, "report_cashflow_count": int(cnt)}
            for end_date, cnt in rows
        ]

    def get_report_cashflow_by_ts_code(self, ts_code: str, **kwargs):
        """
        根据股票代码获取现金流量表数据。
        Args:
            ts_code: 股票代码
            **kwargs: 传递给 get_all 的参数，如 end_date、report_type 等
        Returns:
            现金流量表数据（ORM 实例列表）。
        """
        return self.db.get_all(ReportCashflowEntities, ts_code=ts_code, **kwargs)

    def get_report_cashflow_all(self, *, return_fields: tuple[str, ...] | None = None, **kwargs):
        """
        获取现金流量表全量数据（无筛选条件时即整表；数据量可能很大，请谨慎使用）。
        Args:
            return_fields: 若指定，只查这些列（如 ("ts_code", "end_date")），返回元组列表而非 ORM
            **kwargs: 传递给 get_all / fetch_model_columns 的可选筛选条件
        Returns:
            return_fields 为 None 时为 ORM 实例列表；否则为与列顺序一致的元组列表。
        """
        if return_fields is None:
            return self.db.get_all(ReportCashflowEntities, **kwargs)
        if not return_fields:
            raise ValueError("return_fields 不能为空元组")
        return self.db.fetch_model_columns(ReportCashflowEntities, return_fields, **kwargs)

    def list_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """返回指定报告期全行（dict 列表，供 Load filter 比对）。"""
        rows = self.db.get_all(ReportCashflowEntities, end_date=str(end_date).strip())
        columns = ReportCashflowEntities.__table__.columns
        return [
            {col.name: getattr(row, col.name) for col in columns}
            for row in rows
        ]


if __name__ == "__main__":
    report_cashflow_model = ReportCashflowModel()
    print(report_cashflow_model.get_period_list())
