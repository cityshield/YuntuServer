"""
用户服务
"""
from typing import Optional, List
from uuid import UUID
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.user import User
from app.models.transaction import Transaction, Bill
from app.schemas.user import UserUpdate
from app.services.billing_service import BillingService


class UserService:
    """用户服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.billing_service = BillingService(db)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 用户对象，不存在则返回None
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user_profile(
        self, user_id: UUID, user_update: UserUpdate
    ) -> User:
        """
        更新用户资料

        Args:
            user_id: 用户ID
            user_update: 更新数据

        Returns:
            User: 更新后的用户对象

        Raises:
            HTTPException: 用户不存在或用户名/邮箱已被占用
        """
        # 查询用户
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # 更新字段
        update_data = user_update.model_dump(exclude_unset=True)

        # 检查用户名是否被占用
        if "username" in update_data and update_data["username"] != user.username:
            existing_user = await self.db.execute(
                select(User).where(User.username == update_data["username"])
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists",
                )

        # 检查邮箱是否被占用
        if "email" in update_data and update_data["email"] != user.email:
            existing_user = await self.db.execute(
                select(User).where(User.email == update_data["email"])
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists",
                )

        # 检查手机号是否被占用
        if "phone" in update_data and update_data["phone"] and update_data["phone"] != user.phone:
            existing_user = await self.db.execute(
                select(User).where(User.phone == update_data["phone"])
            )
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already exists",
                )

        # 更新用户信息
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_balance(self, user_id: UUID) -> Decimal:
        """
        获取用户余额

        Args:
            user_id: 用户ID

        Returns:
            Decimal: 用户余额

        Raises:
            HTTPException: 用户不存在
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return user.balance

    async def recharge(
        self, user_id: UUID, amount: Decimal, description: Optional[str] = None
    ) -> User:
        """
        充值

        Args:
            user_id: 用户ID
            amount: 充值金额
            description: 描述

        Returns:
            User: 更新后的用户对象

        Raises:
            HTTPException: 用户不存在或充值金额无效
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recharge amount must be greater than 0",
            )

        return await self.billing_service.recharge_balance(
            user_id=user_id, amount=amount, description=description
        )

    async def get_transactions(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> tuple[List[Transaction], int]:
        """
        获取交易记录

        Args:
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            tuple[List[Transaction], int]: (交易记录列表, 总数)
        """
        # 查询总数
        count_result = await self.db.execute(
            select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # 查询交易记录
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        transactions = result.scalars().all()

        return list(transactions), total

    async def get_bills(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> tuple[List[Bill], int]:
        """
        获取账单记录

        Args:
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            tuple[List[Bill], int]: (账单记录列表, 总数)
        """
        # 查询总数
        count_result = await self.db.execute(
            select(func.count(Bill.id)).where(Bill.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # 查询账单记录
        result = await self.db.execute(
            select(Bill)
            .where(Bill.user_id == user_id)
            .order_by(Bill.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        bills = result.scalars().all()

        return list(bills), total
