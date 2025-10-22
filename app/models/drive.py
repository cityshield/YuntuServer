"""
虚拟盘符模型
"""
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base, UUID


class Drive(Base):
    """虚拟盘符表"""

    __tablename__ = "drives"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(50), nullable=False)  # 盘符名称，如 "C", "D", "项目盘"
    icon = Column(String(50), nullable=True)  # 图标（emoji 或图标类名）
    description = Column(String(255), nullable=True)  # 描述

    # 存储配额
    total_size = Column(BigInteger, nullable=True)  # 总容量限制（字节），NULL 表示无限制
    used_size = Column(BigInteger, default=0, nullable=False)  # 已使用空间（字节）

    # 所有者信息
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=True, index=True)  # 个人盘符
    team_id = Column(UUID(), ForeignKey("teams.id"), nullable=True, index=True)  # 团队盘符
    is_team_drive = Column(Boolean, default=False, nullable=False)  # 是否为团队盘

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)  # 是否启用

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    folders = relationship("Folder", back_populates="drive", cascade="all, delete-orphan")
    files = relationship("File", back_populates="drive", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id], back_populates="drives")

    def __repr__(self):
        return f"<Drive(id={self.id}, name='{self.name}', owner={'team' if self.is_team_drive else 'user'})>"

    @property
    def usage_percentage(self) -> float:
        """计算存储空间使用率"""
        if not self.total_size:
            return 0.0
        return (self.used_size / self.total_size) * 100 if self.total_size > 0 else 0.0

    @property
    def available_size(self) -> int:
        """获取可用空间"""
        if not self.total_size:
            return -1  # 无限制
        return max(0, self.total_size - self.used_size)
