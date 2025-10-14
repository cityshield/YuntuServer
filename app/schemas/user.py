"""
用户相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from decimal import Decimal
import re


class UserBase(BaseModel):
    """用户基础模型"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名",
        examples=["zhangsan"]
    )
    email: EmailStr = Field(
        ...,
        description="邮箱",
        examples=["zhangsan@example.com"]
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="手机号",
        examples=["13800138000"]
    )
    avatar: Optional[str] = Field(
        None,
        max_length=255,
        description="头像URL",
        examples=["https://example.com/avatar.jpg"]
    )


class UserCreate(UserBase):
    """创建用户模型"""

    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="密码",
        examples=["password123"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "zhangsan",
                    "email": "zhangsan@example.com",
                    "phone": "13800138000",
                    "avatar": "https://example.com/avatar.jpg",
                    "password": "password123"
                }
            ]
        }
    }


class UserUpdate(BaseModel):
    """更新用户模型"""

    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        description="用户名",
        examples=["zhangsan"]
    )
    email: Optional[EmailStr] = Field(
        None,
        description="邮箱",
        examples=["zhangsan@example.com"]
    )
    phone: Optional[str] = Field(
        None,
        max_length=20,
        description="手机号",
        examples=["13800138000"]
    )
    avatar: Optional[str] = Field(
        None,
        max_length=255,
        description="头像URL",
        examples=["https://example.com/avatar.jpg"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "zhangsan",
                    "email": "zhangsan@example.com",
                    "phone": "13800138000",
                    "avatar": "https://example.com/avatar.jpg"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """用户响应模型"""

    id: UUID
    username: str
    email: str
    phone: Optional[str]
    avatar: Optional[str]
    balance: Decimal = Field(..., description="余额")
    member_level: int = Field(..., description="会员等级 (0:Free, 1:Basic, 2:Pro, 3:Enterprise)")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """用户资料模型"""

    id: UUID
    username: str
    email: str
    phone: Optional[str]
    avatar: Optional[str]
    member_level: int = Field(..., description="会员等级")
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class BalanceResponse(BaseModel):
    """余额响应模型"""

    balance: Decimal = Field(..., description="当前余额")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "balance": "100.00"
                }
            ]
        }
    }


class RechargeRequest(BaseModel):
    """充值请求模型"""

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="充值金额（必须大于0）",
        examples=["100.00"]
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="备注",
        examples=["支付宝充值"]
    )

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """验证金额精度"""
        if v.as_tuple().exponent < -2:
            raise ValueError('金额最多保留2位小数')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "amount": "100.00",
                    "description": "支付宝充值"
                }
            ]
        }
    }


class UpdateMemberLevelRequest(BaseModel):
    """更新会员等级请求"""

    member_level: int = Field(
        ...,
        ge=0,
        le=3,
        description="会员等级 (0:Free, 1:Basic, 2:Pro, 3:Enterprise)",
        examples=[1]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "member_level": 1
                }
            ]
        }
    }
