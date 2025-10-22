"""
文件模型
"""
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.base import Base, UUID


class UploadSource(str, enum.Enum):
    """上传来源"""
    WEB = "web"  # 网页端上传
    CLIENT = "client"  # 客户端同步上传


class File(Base):
    """文件表"""

    __tablename__ = "files"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)  # 文件名（含扩展名）
    original_name = Column(String(255), nullable=False)  # 原始文件名
    size = Column(BigInteger, nullable=False)  # 文件大小（字节）
    extension = Column(String(50), nullable=True)  # 文件扩展名（如 .jpg, .pdf）
    mime_type = Column(String(100), nullable=True)  # MIME 类型

    # OSS 存储信息
    oss_key = Column(String(512), nullable=False, unique=True, index=True)  # OSS 对象键
    oss_url = Column(String(1024), nullable=True)  # OSS 访问 URL
    thumbnail_url = Column(String(1024), nullable=True)  # 缩略图 URL（用于预览）

    # 文件去重
    md5 = Column(String(32), nullable=False, index=True)  # 文件 MD5 哈希值

    # 关联关系
    drive_id = Column(UUID(), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_id = Column(UUID(), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)  # 根目录文件可以为空

    # 上传信息
    uploaded_by = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)
    upload_source = Column(Enum(UploadSource), default=UploadSource.WEB, nullable=False)  # 上传来源

    # 状态
    is_public = Column(Boolean, default=False, nullable=False)  # 是否公开（生成公开链接）
    is_favorite = Column(Boolean, default=False, nullable=False)  # 是否收藏

    # 软删除
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # 软删除时间戳

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    drive = relationship("Drive", back_populates="files")
    folder = relationship("Folder", back_populates="files")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<File(id={self.id}, name='{self.name}', size={self.size})>"

    @property
    def is_deleted(self) -> bool:
        """是否已删除"""
        return self.deleted_at is not None

    @property
    def size_readable(self) -> str:
        """获取可读的文件大小"""
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @property
    def is_image(self) -> bool:
        """是否为图片文件"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
        return self.extension.lower() in image_extensions if self.extension else False

    @property
    def is_video(self) -> bool:
        """是否为视频文件"""
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'}
        return self.extension.lower() in video_extensions if self.extension else False

    @property
    def is_document(self) -> bool:
        """是否为文档文件"""
        doc_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
        return self.extension.lower() in doc_extensions if self.extension else False
