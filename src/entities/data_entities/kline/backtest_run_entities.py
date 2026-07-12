"""回测运行索引表：对接 warehouse/backtest 与 Admin 历史列表。"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BacktestRunEntities(Base):
    __tablename__ = "backtest_run"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    run_id = Column(String(64), nullable=False, comment="运行 ID")
    backtest_mode = Column(String(16), nullable=False, comment="single / combo")
    factor_name = Column(String(100), comment="单因子名")
    combo_id = Column(Integer, comment="组合 ID")
    combo_name = Column(String(100), comment="组合名冗余")
    start_date = Column(String(8), nullable=False, comment="起始 YYYYMMDD")
    end_date = Column(String(8), nullable=False, comment="结束 YYYYMMDD")
    rebalance = Column(String(16), nullable=False, default="monthly", comment="调仓频率")
    groups = Column(Integer, nullable=False, default=10, comment="分组数")
    status = Column(String(16), nullable=False, default="running", comment="running/success/failed")
    summary_json = Column(JSONB, comment="成功摘要")
    output_dir = Column(Text, comment="warehouse 输出目录")
    error_message = Column(Text, comment="失败信息")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_backtest_run_run_id", "run_id", unique=True),
        Index("idx_backtest_run_created", "created_at"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(BacktestRunEntities, interactive=True)
