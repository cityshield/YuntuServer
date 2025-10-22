"""
文件夹模型（树形结构）
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base, UUID


class Folder(Base):
    """文件夹表（树形结构）"""

    __tablename__ = "folders"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)  # 文件夹名称
    path = Column(String(1024), nullable=False, index=True)  # 完整路径，如 "/Documents/Photos"
    level = Column(Integer, default=0, nullable=False)  # 层级深度，根目录为 0

    # 关联关系
    drive_id = Column(UUID(), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True, index=True)  # 父文件夹 ID

    # 创建者
    created_by = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    drive = relationship("Drive", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], backref="children")
    files = relationship("File", back_populates="folder", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}', path='{self.path}')>"

    def get_breadcrumb(self):
        """获取面包屑路径"""
        if not self.path or self.path == "/":
            return []

        path_parts = self.path.strip("/").split("/")
        breadcrumb = []
        current_path = ""

        for part in path_parts:
            current_path += f"/{part}"
            breadcrumb.append({
                "name": part,
                "path": current_path
            })

        return breadcrumb
