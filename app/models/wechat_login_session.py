"""
微信登录会话模型
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base, UUID


class WechatLoginSession(Base):
    """微信扫码登录会话表"""

    __tablename__ = "wechat_login_sessions"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4, index=True)
    scene_str = Column(String(64), unique=True, nullable=False, index=True)  # 场景值（用于轮询）
    qr_code_url = Column(String(512), nullable=True)  # 二维码URL
    state = Column(String(20), nullable=False, default="pending")  # pending/scanned/confirmed/expired
    wechat_openid = Column(String(128), nullable=True)  # 扫码用户的openid
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=True)  # 关联的用户ID
    device_type = Column(String(20), nullable=False)  # pc/mobile
    session_token = Column(String(255), nullable=True)  # 临时会话token（用于绑定手机号）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 过期时间（5分钟）
    confirmed_at = Column(DateTime(timezone=True), nullable=True)  # 确认登录时间

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<WechatLoginSession {self.scene_str} - {self.state}>"
