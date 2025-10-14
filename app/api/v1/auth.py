"""
认证相关的 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    LoginResponse,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    UserResponse,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账号并返回访问令牌",
)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册

    - **username**: 用户名（3-50个字符）
    - **email**: 邮箱地址
    - **password**: 密码（至少6个字符）
    - **phone**: 手机号（可选）

    返回用户信息和访问令牌
    """
    # 创建用户
    user = await auth_service.register_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        phone=user_data.phone,
    )

    # 生成令牌
    access_token, refresh_token, expires_in = await auth_service.create_tokens(
        db=db, user=user
    )

    # 提交事务
    await db.commit()
    await db.refresh(user)

    # 构造响应
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="用户登录",
    description="使用邮箱和密码登录，返回访问令牌",
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录

    - **username**: 用户名或邮箱
    - **password**: 密码

    返回用户信息和访问令牌
    """
    # 验证用户凭证 - 支持用户名或邮箱登录
    user = await auth_service.authenticate_user(
        db=db,
        identifier=credentials.username,
        password=credentials.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成令牌
    access_token, refresh_token, expires_in = await auth_service.create_tokens(
        db=db, user=user
    )

    # 提交事务
    await db.commit()
    await db.refresh(user)

    # 构造响应
    return LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="刷新访问令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌

    返回新的访问令牌
    """
    # 刷新访问令牌
    new_access_token, expires_in = await auth_service.refresh_access_token(
        db=db,
        refresh_token=token_data.refresh_token,
    )

    # 提交事务
    await db.commit()

    # 构造响应
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=token_data.refresh_token,  # 刷新令牌保持不变
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="用户登出",
    description="登出并撤销刷新令牌",
)
async def logout(
    token_data: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登出

    - **refresh_token**: 刷新令牌

    撤销刷新令牌，使其失效
    """
    # 删除刷新令牌
    await auth_service.logout(
        db=db,
        refresh_token=token_data.refresh_token,
    )

    # 提交事务
    await db.commit()

    return {
        "message": "Successfully logged out",
        "success": True,
    }
