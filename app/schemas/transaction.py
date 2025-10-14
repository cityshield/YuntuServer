"""
交易和账单相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field
from decimal import Decimal


class TransactionBase(BaseModel):
    """交易基础模型"""

    type: str = Field(..., max_length=50, description="交易类型 recharge, consume, refund")
    amount: Decimal = Field(..., description="交易金额")
    description: Optional[str] = Field(None, description="描述")


class TransactionResponse(TransactionBase):
    """交易响应模型"""

    id: UUID
    user_id: UUID
    balance_after: Optional[Decimal] = Field(None, description="交易后余额")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """交易列表响应模型"""

    transactions: list[TransactionResponse]
    total: int
    skip: int
    limit: int


class BillBase(BaseModel):
    """账单基础模型"""

    amount: Decimal = Field(..., description="账单金额")
    description: Optional[str] = Field(None, description="描述")


class BillResponse(BillBase):
    """账单响应模型"""

    id: UUID
    user_id: UUID
    task_id: Optional[UUID] = Field(None, description="关联任务ID")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class BillListResponse(BaseModel):
    """账单列表响应模型"""

    bills: list[BillResponse]
    total: int
    skip: int
    limit: int
