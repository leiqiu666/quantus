from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, create_engine, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
from src.common.setting import settings

# create base class (模块级别，可被其他模块导入使用)
Base = declarative_base()

class LogMissing(Base):
    __tablename__ = "log_missing"
    id = Column(Integer, primary_key=True,autoincrement=True,comment="ID")
    ts_code = Column(String(20),comment="股票代码")
    missing_entity = Column(String(100),comment="缺失实体")
    missing_date = Column(String(8),comment="缺失日期")
    try_count = Column(Integer,comment="尝试次数")
    last_try_time = Column(DateTime,comment="最后尝试时间")

    __table_args__ = (
        Index('idx_log_missing_ts_code', 'ts_code'),
        Index('idx_log_missing_missing_entity', 'missing_entity'),
        Index('idx_log_missing_missing_date', 'missing_date'),
        Index('idx_log_missing_try_count', 'try_count'),
        Index('idx_log_missing_last_try_time', 'last_try_time'),
        # 唯一索引 ts_code + missing_entity + missing_date
        Index('idx_log_missing_unique', 'ts_code', 'missing_entity', 'missing_date', unique=True),
    )
if __name__ == "__main__":
    from src.common.database import sync_table
    
    # 使用通用函数同步表结构
    sync_table(LogMissing)