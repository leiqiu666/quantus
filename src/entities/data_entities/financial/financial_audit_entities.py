"""财务审计意见（Tushare fina_audit）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FinaAuditEntities(Base):
    __tablename__ = "financial_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    ann_date = Column(String(8), comment="公告日期")
    end_date = Column(String(8), comment="报告期")
    audit_result = Column(String(40), comment="审计结果")
    audit_fees = Column(Float, comment="审计费用（元）")
    audit_agency = Column(String(200), comment="会计事务所")
    audit_sign = Column(String(100), comment="签字会计师")

    __table_args__ = (
        Index("idx_fina_audit_end_date", "end_date"),
        Index("idx_fina_audit_ts_code", "ts_code"),
        Index("idx_fina_audit_unique", "ts_code", "end_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(FinaAuditEntities)
