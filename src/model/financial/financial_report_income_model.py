from typing import Any, Dict, List, Optional

from sqlalchemy import func

from src.common.database import Database
from src.entities.data_entities.financial.financial_report_income_entities import ReportIncomeEntities


class ReportIncomeModel:
    def __init__(self):
        self.db = Database()

    def get_period_list(
        self,
        *,
        start_period_date: Optional[str] = None,
        end_period_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取利润表报告期列表
        Args:
            start_period_date: 报告期下界（含），YYYYMMDD；与表字段 end_date 区分命名
            end_period_date: 报告期上界（含），YYYYMMDD
        逻辑:
            1. report_income 表中 end_date 为报告期
            2. 根据 end_date 分组统计条数，可按 start_period_date / end_period_date 筛选（字符串比较，适用于 YYYYMMDD）
        Returns:
            报告期列表（按 report_period 即 end_date 倒序，新到旧），元素含 report_period、report_income_count
        """
        clauses = [
            ReportIncomeEntities.end_date.isnot(None),
            ReportIncomeEntities.end_date != "",
        ]
        if start_period_date is not None:
            clauses.append(ReportIncomeEntities.end_date >= start_period_date)
        if end_period_date is not None:
            clauses.append(ReportIncomeEntities.end_date <= end_period_date)
        rows = self.db.select_grouped(
            ReportIncomeEntities,
            ReportIncomeEntities.end_date,
            func.count(ReportIncomeEntities.id),
            group_by=(ReportIncomeEntities.end_date,),
            order_by=(ReportIncomeEntities.end_date.desc(),),
            where_clauses=tuple(clauses),
        )
        return [
            {"report_period": end_date, "report_income_count": int(cnt)}
            for end_date, cnt in rows
        ]

    def get_report_income_by_ts_code(self, ts_code: str, **kwargs):
        """
        根据股票代码获取财报数据。
        Args:
            ts_code: 股票代码
            **kwargs: 传递给 get_all 的参数，如 end_date、report_type 等
        Returns:
            财报数据（ORM 实例列表）。
        """
        return self.db.get_all(ReportIncomeEntities, ts_code=ts_code, **kwargs)

    def get_report_income_all(self, *, return_fields: tuple[str, ...] | None = None, **kwargs):
        """
        获取利润表全量数据（无 ts_code 等条件时即整表；数据量可能很大，请谨慎使用）。
        Args:
            return_fields: 若指定，只查这些列（如 ("ts_code", "end_date")），返回元组列表而非 ORM
            **kwargs: 传递给 get_all / fetch_model_columns 的可选筛选条件
        Returns:
            return_fields 为 None 时为 ORM 实例列表；否则为与列顺序一致的元组列表。
        """
        if return_fields is None:
            return self.db.get_all(ReportIncomeEntities, **kwargs)
        if not return_fields:
            raise ValueError("return_fields 不能为空元组")
        return self.db.fetch_model_columns(ReportIncomeEntities, return_fields, **kwargs)

    def list_by_end_date(self, end_date: str) -> List[Dict[str, Any]]:
        """返回指定报告期全行（dict 列表，供 Load filter 比对）。"""
        rows = self.db.get_all(ReportIncomeEntities, end_date=str(end_date).strip())
        columns = ReportIncomeEntities.__table__.columns
        return [
            {col.name: getattr(row, col.name) for col in columns}
            for row in rows
        ]


if __name__ == "__main__":
    report_income_model = ReportIncomeModel()
    print(report_income_model.get_period_list())