"""
依赖注入模块
"""
from typing import AsyncGenerator, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.core.security import decode_token, verify_token_type
from app.models.user import User
from app.models.task import Task

# HTTP Bearer 认证方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前用户（依赖注入）

    Args:
        credentials: HTTP Bearer 凭证
        db: 数据库会话

    Returns:
        User: 当前登录用户对象

    Raises:
        HTTPException: 401 - Token无效或用户不存在
    """
    # 解码token
    token = credentials.credentials
    payload = decode_token(token)

    # 验证token类型
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户ID
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户（依赖注入）

    Args:
        current_user: 当前用户

    Returns:
        User: 当前活跃用户对象

    Raises:
        HTTPException: 403 - 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    根据用户ID获取用户（依赖注入）

    Args:
        user_id: 用户ID
        db: 数据库会话

    Returns:
        User: 用户对象

    Raises:
        HTTPException: 404 - 用户不存在
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def get_task_by_id(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Task:
    """
    根据任务ID获取任务（依赖注入）

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        Task: 任务对象

    Raises:
        HTTPException: 404 - 任务不存在
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


async def verify_task_owner(
    task: Task = Depends(get_task_by_id),
    current_user: User = Depends(get_current_active_user),
) -> Task:
    """
    验证任务所有者（依赖注入）

    Args:
        task: 任务对象
        current_user: 当前用户

    Returns:
        Task: 任务对象

    Raises:
        HTTPException: 403 - 无权限访问该任务
    """
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this task",
        )

    return task


class PaginationParams:
    """分页参数（依赖注入）"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    ):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size
        self.limit = page_size


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    获取可选的当前用户（依赖注入）
    用于某些既支持认证也支持非认证访问的接口

    Args:
        credentials: HTTP Bearer 凭证（可选）
        db: 数据库会话

    Returns:
        Optional[User]: 当前用户对象，如果未认证则返回None
    """
    if credentials is None:
        return None

    try:
        # 解码token
        token = credentials.credentials
        payload = decode_token(token)

        # 验证token类型
        if not verify_token_type(payload, "access"):
            return None

        # 获取用户ID
        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        # 查询用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        return user if user and user.is_active else None
    except Exception:
        return None


def check_member_level(required_level: int):
    """
    检查用户会员等级（依赖注入工厂函数）

    Args:
        required_level: 所需的会员等级

    Returns:
        依赖注入函数
    """
    async def _check_member_level(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.member_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Member level {required_level} or higher required",
            )
        return current_user

    return _check_member_level
