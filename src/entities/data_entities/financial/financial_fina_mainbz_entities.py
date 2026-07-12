"""主营业务构成（Tushare fina_mainbz）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FinaMainbzEntities(Base):
    __tablename__ = "financial_fina_mainbz"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    end_date = Column(String(8), comment="报告期")
    bz_item = Column(String(200), comment="主营业务来源")
    bz_code = Column(String(20), comment="主营业务来源类型")
    bz_sales = Column(Float, comment="主营业务收入(元)")
    bz_profit = Column(Float, comment="主营业务利润(元)")
    bz_cost = Column(Float, comment="主营业务成本(元)")
    curr_type = Column(String(10), comment="货币代码")
    update_flag = Column(String(4), comment="是否更新")

    __table_args__ = (
        Index("idx_fina_mainbz_end_date", "end_date"),
        Index("idx_fina_mainbz_ts_code", "ts_code"),
        Index(
            "idx_fina_mainbz_unique",
            "ts_code",
            "end_date",
            "bz_item",
            "bz_code",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(FinaMainbzEntities)
