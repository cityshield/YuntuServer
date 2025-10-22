"""
团队模型
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base, UUID


class Team(Base):
    """团队表"""

    __tablename__ = "teams"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)  # 团队名称
    description = Column(Text, nullable=True)  # 团队描述
    avatar = Column(String(512), nullable=True)  # 团队头像 URL

    # 创建者/所有者
    owner_id = Column(UUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 团队设置
    is_active = Column(Boolean, default=True, nullable=False)  # 是否启用
    max_members = Column(String(10), nullable=True)  # 最大成员数限制，NULL 表示无限制

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    drives = relationship("Drive", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"

    @property
    def member_count(self) -> int:
        """获取成员数量"""
        return len(self.members) if self.members else 0

    @property
    def is_full(self) -> bool:
        """团队是否已满"""
        if not self.max_members:
            return False
        return self.member_count >= int(self.max_members)
