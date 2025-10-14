"""
认证服务：处理用户注册、登录、Token管理等逻辑
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status

from app.models import User, RefreshToken
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)
from app.config import settings


class AuthService:
    """认证服务类"""

    async def register_user(
        self,
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
    ) -> User:
        """
        用户注册

        Args:
            db: 数据库会话
            username: 用户名
            email: 邮箱
            password: 密码
            phone: 手机号（可选）

        Returns:
            User: 创建的用户对象

        Raises:
            HTTPException: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        result = await db.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        # 检查邮箱是否已存在
        result = await db.execute(select(User).where(User.email == email))
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # 检查手机号是否已存在（如果提供）
        if phone:
            result = await db.execute(select(User).where(User.phone == phone))
            existing_phone = result.scalar_one_or_none()
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered",
                )

        # 创建新用户
        hashed_password = get_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            phone=phone,
            balance=0.00,
            member_level=0,
            is_active=True,
            last_login_at=datetime.utcnow(),
        )

        db.add(new_user)
        await db.flush()
        await db.refresh(new_user)

        return new_user

    async def authenticate_user(
        self, db: AsyncSession, identifier: str, password: str
    ) -> Optional[User]:
        """
        验证用户凭证（支持用户名或邮箱登录）

        Args:
            db: 数据库会话
            identifier: 用户名或邮箱
            password: 密码

        Returns:
            Optional[User]: 验证成功返回用户对象，失败返回None
        """
        # 查找用户（支持用户名或邮箱）
        # 判断是邮箱还是用户名
        if "@" in identifier:
            # 使用邮箱查找
            result = await db.execute(select(User).where(User.email == identifier))
        else:
            # 使用用户名查找
            result = await db.execute(select(User).where(User.username == identifier))

        user = result.scalar_one_or_none()

        if not user:
            return None

        # 验证密码
        if not verify_password(password, user.password_hash):
            return None

        # 检查用户是否激活
        if not user.is_active:
            return None

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        await db.flush()

        return user

    async def create_tokens(self, db: AsyncSession, user: User) -> Tuple[str, str, int]:
        """
        创建访问令牌和刷新令牌

        Args:
            db: 数据库会话
            user: 用户对象

        Returns:
            Tuple[str, str, int]: (access_token, refresh_token, expires_in)
        """
        # 创建访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires,
        )

        # 创建刷新令牌
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # 将刷新令牌存储到数据库
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token_record = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )
        db.add(refresh_token_record)
        await db.flush()

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 转换为秒

        return access_token, refresh_token, expires_in

    async def refresh_access_token(
        self, db: AsyncSession, refresh_token: str
    ) -> Tuple[str, int]:
        """
        使用刷新令牌获取新的访问令牌

        Args:
            db: 数据库会话
            refresh_token: 刷新令牌

        Returns:
            Tuple[str, int]: (new_access_token, expires_in)

        Raises:
            HTTPException: 令牌无效或已过期
        """
        # 解码刷新令牌
        try:
            payload = decode_token(refresh_token)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # 验证令牌类型
        if not verify_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # 从数据库中查找刷新令牌
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found",
            )

        # 检查令牌是否过期
        if token_record.expires_at < datetime.utcnow():
            # 删除过期的令牌
            await db.delete(token_record)
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        # 获取用户信息
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # 创建新的访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires,
        )

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 转换为秒

        return new_access_token, expires_in

    async def logout(self, db: AsyncSession, refresh_token: str) -> bool:
        """
        用户登出，删除刷新令牌

        Args:
            db: 数据库会话
            refresh_token: 刷新令牌

        Returns:
            bool: 是否成功登出

        Raises:
            HTTPException: 令牌无效
        """
        # 从数据库中查找并删除刷新令牌
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.token == refresh_token)
        )

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refresh token not found",
            )

        await db.flush()
        return True

    async def delete_expired_tokens(self, db: AsyncSession) -> int:
        """
        删除所有过期的刷新令牌（后台任务）

        Args:
            db: 数据库会话

        Returns:
            int: 删除的令牌数量
        """
        result = await db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        await db.flush()
        return result.rowcount


# 创建全局认证服务实例
auth_service = AuthService()
