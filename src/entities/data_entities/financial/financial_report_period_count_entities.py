"""Report period count entities"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from src.common.setting import settings

Base = declarative_base()

class ReportPeriodCountEntities(Base):
    __tablename__ = "financial_report_period_count"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    report_period = Column(String(8), comment="报告期")
    period_stock_count = Column(Integer, comment="该期股票数")
    report_income_count = Column(Integer, comment="利润表该期记录数")
    report_balance_count = Column(Integer, comment="资产负债表该期记录数")
    report_cashflow_count = Column(Integer, comment="现金流量表该期记录数")
    report_indicator_count = Column(Integer, default=0, comment="财务指标该期记录数")

    __table_args__ = (
        Index(
            'idx_report_period_count_report_period',
            'report_period',
            unique=True,
        ),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(ReportPeriodCountEntities)