"""
团队成员模型
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.db.base import Base, UUID


class TeamRole(str, enum.Enum):
    """团队角色"""
    OWNER = "owner"  # 所有者（创建者）
    ADMIN = "admin"  # 管理员（可管理成员和文件）
    MEMBER = "member"  # 普通成员（可读写文件）
    VIEWER = "viewer"  # 访客（只读权限）


class TeamMember(Base):
    """团队成员表"""

    __tablename__ = "team_members"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)

    # 关联关系
    team_id = Column(UUID(), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 角色和权限
    role = Column(Enum(TeamRole), default=TeamRole.MEMBER, nullable=False)

    # 权限细分
    can_upload = Column(Boolean, default=True, nullable=False)  # 是否可以上传文件
    can_delete = Column(Boolean, default=False, nullable=False)  # 是否可以删除文件
    can_share = Column(Boolean, default=True, nullable=False)  # 是否可以分享文件
    can_manage_members = Column(Boolean, default=False, nullable=False)  # 是否可以管理成员

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)  # 是否启用

    # 邀请信息
    invited_by = Column(UUID(), ForeignKey("users.id"), nullable=True)  # 邀请人
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 加入时间

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    team = relationship("Team", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])

    # 唯一约束：同一用户不能重复加入同一团队
    __table_args__ = (
        UniqueConstraint('team_id', 'user_id', name='uq_team_user'),
    )

    def __repr__(self):
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id}, role={self.role})>"

    @property
    def is_owner(self) -> bool:
        """是否为团队所有者"""
        return self.role == TeamRole.OWNER

    @property
    def is_admin(self) -> bool:
        """是否为管理员或所有者"""
        return self.role in [TeamRole.OWNER, TeamRole.ADMIN]

    @property
    def has_write_permission(self) -> bool:
        """是否有写权限"""
        return self.role in [TeamRole.OWNER, TeamRole.ADMIN, TeamRole.MEMBER] and self.can_upload

    @property
    def has_delete_permission(self) -> bool:
        """是否有删除权限"""
        return self.role in [TeamRole.OWNER, TeamRole.ADMIN] or self.can_delete
