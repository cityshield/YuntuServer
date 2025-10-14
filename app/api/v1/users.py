"""
用户相关API端点
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    BalanceResponse,
    RechargeRequest,
)
from app.schemas.transaction import TransactionListResponse, BillListResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    获取当前用户信息

    Args:
        current_user: 当前登录用户

    Returns:
        UserResponse: 用户信息
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新用户资料

    Args:
        user_update: 更新数据
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UserResponse: 更新后的用户信息
    """
    user_service = UserService(db)
    updated_user = await user_service.update_user_profile(
        user_id=current_user.id, user_update=user_update
    )
    return updated_user


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户余额

    Args:
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        BalanceResponse: 余额信息
    """
    user_service = UserService(db)
    balance = await user_service.get_balance(current_user.id)
    return {"balance": balance}


@router.post("/recharge", response_model=UserResponse)
async def recharge(
    recharge_data: RechargeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    充值

    Args:
        recharge_data: 充值数据
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UserResponse: 更新后的用户信息
    """
    user_service = UserService(db)
    updated_user = await user_service.recharge(
        user_id=current_user.id,
        amount=recharge_data.amount,
        description=recharge_data.description,
    )
    return updated_user


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取交易记录

    Args:
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TransactionListResponse: 交易记录列表
    """
    user_service = UserService(db)
    transactions, total = await user_service.get_transactions(
        user_id=current_user.id, skip=skip, limit=limit
    )
    return {
        "transactions": transactions,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/bills", response_model=BillListResponse)
async def get_bills(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取账单记录

    Args:
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        BillListResponse: 账单记录列表
    """
    user_service = UserService(db)
    bills, total = await user_service.get_bills(
        user_id=current_user.id, skip=skip, limit=limit
    )
    return {
        "bills": bills,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
