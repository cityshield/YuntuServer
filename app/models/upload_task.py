"""
上传任务模型
"""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.base import Base, UUID


class TaskStatus(str, enum.Enum):
    """任务状态"""
    PENDING = "pending"  # 待上传
    UPLOADING = "uploading"  # 上传中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class UploadTask(Base):
    """上传任务表"""

    __tablename__ = "upload_tasks"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # 关联关系
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    drive_id = Column(UUID(), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)

    # 任务基本信息
    task_name = Column(String(255), nullable=False)  # 任务名称
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    priority = Column(Integer, default=5, nullable=False)  # 优先级 0-10

    # 进度追踪
    total_files = Column(Integer, default=0, nullable=False)  # 总文件数
    uploaded_files = Column(Integer, default=0, nullable=False)  # 已上传文件数
    total_size = Column(BigInteger, default=0, nullable=False)  # 总大小（字节）
    uploaded_size = Column(BigInteger, default=0, nullable=False)  # 已上传大小（字节）

    # 描述文件（JSON 格式存储）
    upload_manifest = Column(JSON, nullable=True)  # 客户端提交的上传描述
    storage_manifest = Column(JSON, nullable=True)  # 服务端生成的存储描述

    # 错误处理
    error_message = Column(Text, nullable=True)  # 错误信息
    retry_count = Column(Integer, default=0, nullable=False)  # 重试次数

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完成时间

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    drive = relationship("Drive", foreign_keys=[drive_id])
    task_files = relationship("TaskFile", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UploadTask(id={self.id}, name='{self.task_name}', status={self.status})>"

    @property
    def progress_percentage(self) -> float:
        """计算任务进度百分比（基于文件数）"""
        if self.total_files == 0:
            return 0.0
        return (self.uploaded_files / self.total_files) * 100

    @property
    def size_progress_percentage(self) -> float:
        """计算任务进度百分比（基于大小）"""
        if self.total_size == 0:
            return 0.0
        return (self.uploaded_size / self.total_size) * 100

    @property
    def remaining_files(self) -> int:
        """获取剩余文件数"""
        return max(0, self.total_files - self.uploaded_files)

    @property
    def remaining_size(self) -> int:
        """获取剩余大小（字节）"""
        return max(0, self.total_size - self.uploaded_size)

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_in_progress(self) -> bool:
        """是否正在进行中"""
        return self.status in [TaskStatus.PENDING, TaskStatus.UPLOADING]
