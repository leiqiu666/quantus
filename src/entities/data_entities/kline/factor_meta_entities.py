"""因子元数据表：记录系统中所有因子的名称、来源、覆盖区间等。"""

from sqlalchemy import Column, Integer, String, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FactorMetaEntities(Base):
    __tablename__ = "factor_meta"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    factor_name = Column(String(100), nullable=False, comment="因子名称（唯一）")
    display_name = Column(String(200), comment="中文名称")
    source = Column(String(50), nullable=False, comment="来源：自研 / tushare / 国泰191")
    category = Column(String(50), comment="分类：量价 / 基本面 / 技术 / 统计")
    formula = Column(Text, comment="算法说明或可编辑公式")
    impl_kind = Column(
        String(32),
        nullable=True,
        default="tushare",
        comment="formula / python / tushare",
    )
    python_path = Column(String(300), comment="相对仓库的 Python 源码路径")
    start_date = Column(String(8), comment="Parquet 最早交易日 YYYYMMDD")
    end_date = Column(String(8), comment="Parquet 最晚交易日 YYYYMMDD")
    month_count = Column(Integer, comment="已有 Parquet 月份数")

    __table_args__ = (
        Index("idx_factor_meta_name", "factor_name", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(FactorMetaEntities, interactive=True)
