"""
任务模型
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class Task(Base):
    """任务表"""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_name = Column(String(200), nullable=False)
    scene_file = Column(String(500))
    maya_version = Column(String(20))
    renderer = Column(String(50))
    status = Column(Integer, default=0, nullable=False, index=True)  # 0:Draft, 1:Pending, 2:Queued, 3:Rendering, 4:Paused, 5:Completed, 6:Failed, 7:Cancelled
    priority = Column(Integer, default=1, nullable=False)  # 0:Low, 1:Normal, 2:High, 3:Urgent
    progress = Column(Integer, default=0, nullable=False)
    start_frame = Column(Integer)
    end_frame = Column(Integer)
    frame_step = Column(Integer, default=1)
    width = Column(Integer)
    height = Column(Integer)
    output_path = Column(String(500))
    output_format = Column(String(20))
    estimated_cost = Column(Numeric(10, 2))
    actual_cost = Column(Numeric(10, 2))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task {self.task_name}>"


class TaskLog(Base):
    """任务日志表"""

    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    log_level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    task = relationship("Task", back_populates="logs")

    def __repr__(self):
        return f"<TaskLog {self.task_id} - {self.log_level}>"
