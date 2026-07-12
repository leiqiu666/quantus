"""业绩预告（Tushare forecast_vip）。"""

from sqlalchemy import Column, Integer, Float, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ForecastEntities(Base):
    __tablename__ = "financial_forecast"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    ann_date = Column(String(8), comment="公告日期")
    end_date = Column(String(8), comment="报告期")
    type = Column(String(20), comment="预告类型")
    p_change_min = Column(Float, comment="变动幅度下限(%)")
    p_change_max = Column(Float, comment="变动幅度上限(%)")
    net_profit_min = Column(Float, comment="净利润下限（万元）")
    net_profit_max = Column(Float, comment="净利润上限（万元）")
    last_parent_net = Column(Float, comment="上年同期净利润")
    first_ann_date = Column(String(8), comment="首次公告日")
    summary = Column(Text, comment="业绩预告摘要")
    change_reason = Column(Text, comment="业绩变动原因")

    __table_args__ = (
        Index("idx_forecast_end_date", "end_date"),
        Index("idx_forecast_ts_code", "ts_code"),
        Index("idx_forecast_unique", "ts_code", "end_date", "ann_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(ForecastEntities)
