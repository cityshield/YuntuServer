"""
计费服务
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.task import Task
from app.models.transaction import Transaction, Bill
from app.config import settings


class BillingService:
    """计费服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_task_cost(self, task: Task) -> Decimal:
        """
        计算任务费用

        Args:
            task: 任务对象

        Returns:
            Decimal: 任务费用
        """
        if task.start_frame is None or task.end_frame is None:
            return Decimal("0.00")

        # 计算总帧数
        total_frames = (task.end_frame - task.start_frame + 1) // task.frame_step

        # 计算费用 = 帧数 * 每帧价格
        cost_per_frame = Decimal(str(settings.RENDER_COST_PER_FRAME))
        total_cost = total_frames * cost_per_frame

        return Decimal(str(round(float(total_cost), 2)))

    async def deduct_balance(
        self, user_id: UUID, amount: Decimal, description: Optional[str] = None
    ) -> User:
        """
        扣除用户余额

        Args:
            user_id: 用户ID
            amount: 扣除金额
            description: 描述

        Returns:
            User: 更新后的用户对象

        Raises:
            HTTPException: 余额不足或用户不存在
        """
        # 查询用户
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # 检查余额
        if user.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient balance",
            )

        # 扣除余额
        user.balance -= amount

        # 创建交易记录
        await self.create_transaction(
            user_id=user_id,
            transaction_type="consume",
            amount=-amount,
            balance_after=user.balance,
            description=description,
        )

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def create_transaction(
        self,
        user_id: UUID,
        transaction_type: str,
        amount: Decimal,
        balance_after: Optional[Decimal] = None,
        description: Optional[str] = None,
    ) -> Transaction:
        """
        创建交易记录

        Args:
            user_id: 用户ID
            transaction_type: 交易类型 (recharge, consume, refund)
            amount: 交易金额
            balance_after: 交易后余额
            description: 描述

        Returns:
            Transaction: 交易记录对象
        """
        transaction = Transaction(
            user_id=user_id,
            type=transaction_type,
            amount=amount,
            balance_after=balance_after,
            description=description,
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)

        return transaction

    async def create_bill(
        self,
        user_id: UUID,
        amount: Decimal,
        task_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> Bill:
        """
        创建账单

        Args:
            user_id: 用户ID
            amount: 账单金额
            task_id: 关联任务ID
            description: 描述

        Returns:
            Bill: 账单对象
        """
        bill = Bill(
            user_id=user_id,
            task_id=task_id,
            amount=amount,
            description=description,
        )

        self.db.add(bill)
        await self.db.commit()
        await self.db.refresh(bill)

        return bill

    async def recharge_balance(
        self, user_id: UUID, amount: Decimal, description: Optional[str] = None
    ) -> User:
        """
        充值余额

        Args:
            user_id: 用户ID
            amount: 充值金额
            description: 描述

        Returns:
            User: 更新后的用户对象

        Raises:
            HTTPException: 用户不存在
        """
        # 查询用户
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # 增加余额
        user.balance += amount

        # 创建交易记录
        await self.create_transaction(
            user_id=user_id,
            transaction_type="recharge",
            amount=amount,
            balance_after=user.balance,
            description=description or "Account recharge",
        )

        await self.db.commit()
        await self.db.refresh(user)

        return user
