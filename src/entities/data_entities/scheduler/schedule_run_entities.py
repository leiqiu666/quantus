"""调度执行记录实体"""

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ScheduleRunEntities(Base):
    __tablename__ = "schedule_run"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    job_id = Column(Integer, nullable=True, comment="schedule_job.id")
    triggered_by = Column(String(16), nullable=False, comment="cron / manual / admin")
    status = Column(String(16), nullable=False, comment="running / success / failed / partial / skipped")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    error_message = Column(Text, nullable=True, comment="错误摘要")

    __table_args__ = (
        Index("idx_schedule_run_job_id", "job_id"),
        Index("idx_schedule_run_status", "status"),
        Index("idx_schedule_run_started_at", "started_at"),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(ScheduleRunEntities)
