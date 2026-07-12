"""因子热层宽表 — 固定列定义，因子列由 FactorSyncService 动态管理。"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

from src.common.setting import settings

Base = declarative_base()


class FactorLatestEntities(Base):
    __tablename__ = "factor_latest"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(String(8), nullable=False, comment="交易日 YYYYMMDD")

    __table_args__ = (
        Index("idx_factor_latest_code_date", "ts_code", "trade_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(FactorLatestEntities, interactive=True)
