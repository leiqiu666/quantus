"""每日活跃股票数快照：未退市 / 应交易两种口径。"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StockActiveCountEntities(Base):
    __tablename__ = "stock_active_count"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    date_key = Column(String(8), comment="日期键 YYYYMMDD（开市日或报告期）")
    listed_count = Column(Integer, comment="当日未退市 A 股数（不含 B 股）")
    trading_count = Column(Integer, comment="当日应交易股数（listed - 全天停牌）；非开市日为空")

    __table_args__ = (
        Index(
            "idx_stock_active_count_date_key",
            "date_key",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(StockActiveCountEntities)
