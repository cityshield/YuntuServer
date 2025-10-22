"""
任务文件模型
"""
from sqlalchemy import Column, String, Integer, BigInteger, Float, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.base import Base, UUID


class FileUploadStatus(str, enum.Enum):
    """文件上传状态"""
    PENDING = "pending"  # 待上传
    UPLOADING = "uploading"  # 上传中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    SKIPPED = "skipped"  # 跳过（秒传）


class TaskFile(Base):
    """任务文件关系表"""

    __tablename__ = "task_files"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # 关联关系
    task_id = Column(UUID(), ForeignKey("upload_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(), ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True)  # 上传成功后关联

    # 文件源信息（来自客户端）
    local_path = Column(String(1024), nullable=False)  # 客户端本地路径
    target_folder_path = Column(String(1024), nullable=False)  # 目标文件夹虚拟路径
    file_name = Column(String(255), nullable=False)  # 文件名
    file_size = Column(BigInteger, nullable=False)  # 文件大小（字节）
    md5 = Column(String(32), nullable=True, index=True)  # MD5 哈希值
    mime_type = Column(String(100), nullable=True)  # MIME 类型

    # 上传状态
    status = Column(Enum(FileUploadStatus), default=FileUploadStatus.PENDING, nullable=False, index=True)
    upload_progress = Column(Float, default=0.0, nullable=False)  # 上传进度 0-100

    # OSS 存储信息
    oss_key = Column(String(512), nullable=True, index=True)  # OSS 对象键
    oss_url = Column(String(1024), nullable=True)  # OSS 访问 URL

    # 分片上传支持
    chunk_info = Column(JSON, nullable=True)  # 分片上传信息

    # 错误处理
    error_message = Column(Text, nullable=True)  # 错误信息
    retry_count = Column(Integer, default=0, nullable=False)  # 重试次数

    # 秒传标记
    is_duplicated = Column(Boolean, default=False, nullable=False)  # 是否秒传
    duplicated_from = Column(UUID(), ForeignKey("files.id", ondelete="SET NULL"), nullable=True)  # 引用的原文件

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 完成时间

    # 关系
    task = relationship("UploadTask", back_populates="task_files")
    file = relationship("File", foreign_keys=[file_id])
    duplicated_source = relationship("File", foreign_keys=[duplicated_from])

    def __repr__(self):
        return f"<TaskFile(id={self.id}, name='{self.file_name}', status={self.status})>"

    @property
    def virtual_path(self) -> str:
        """获取完整的虚拟路径"""
        folder_path = self.target_folder_path.rstrip("/")
        return f"{folder_path}/{self.file_name}"

    @property
    def is_completed(self) -> bool:
        """是否已完成（包括上传和秒传）"""
        return self.status in [FileUploadStatus.COMPLETED, FileUploadStatus.SKIPPED]

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == FileUploadStatus.FAILED

    @property
    def can_retry(self) -> bool:
        """是否可以重试"""
        return self.is_failed and self.retry_count < 3  # 最多重试3次

    @property
    def is_large_file(self) -> bool:
        """是否为大文件（需要分片上传）"""
        return self.file_size >= 5 * 1024 * 1024  # >= 5MB

    @property
    def chunk_progress(self) -> dict:
        """获取分片上传进度信息"""
        if not self.chunk_info:
            return {}

        total_chunks = self.chunk_info.get("total_chunks", 0)
        uploaded_chunks = self.chunk_info.get("uploaded_chunks", [])

        return {
            "total_chunks": total_chunks,
            "uploaded_chunks_count": len(uploaded_chunks),
            "progress_percentage": (len(uploaded_chunks) / total_chunks * 100) if total_chunks > 0 else 0.0,
        }
