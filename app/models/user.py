"""
用户模型
"""
from sqlalchemy import Column, String, Boolean, Numeric, DateTime, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base, UUID


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)  # 邮箱可选
    phone = Column(String(20), unique=True, nullable=False, index=True)  # 手机号必填
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    balance = Column(Numeric(10, 2), default=0.00, nullable=False)
    member_level = Column(Integer, default=0, nullable=False)  # 0:Free, 1:Basic, 2:Pro, 3:Enterprise
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # 微信相关字段
    wechat_openid = Column(String(128), unique=True, nullable=True, index=True)  # 微信开放平台 OpenID
    wechat_unionid = Column(String(128), unique=True, nullable=True, index=True)  # 微信 UnionID
    wechat_nickname = Column(String(100), nullable=True)  # 微信昵称
    wechat_avatar = Column(String(255), nullable=True)  # 微信头像URL
    wechat_bound_at = Column(DateTime(timezone=True), nullable=True)  # 微信绑定时间

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"
