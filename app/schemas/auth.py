"""
认证相关的 Schema
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名或邮箱",
        examples=["zhangsan"]
    )
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
                    "password": "password123"
                }
            ]
        }
    }


class SendCodeRequest(BaseModel):
    """发送验证码请求"""

    phone: str = Field(
        ...,
        max_length=20,
        description="手机号码",
        examples=["13800138000"]
    )

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """验证手机号格式"""
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "phone": "13800138000"
                }
            ]
        }
    }


class SendCodeResponse(BaseModel):
    """发送验证码响应"""

    success: bool = Field(..., description="是否发送成功")
    message: str = Field(..., description="响应消息")
    request_id: Optional[str] = Field(None, description="请求ID")


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名（3-50个字符，只能包含字母、数字、下划线）",
        examples=["zhangsan"]
    )
    phone: str = Field(
        ...,
        max_length=20,
        description="手机号码",
        examples=["13800138000"]
    )
    verification_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="短信验证码（6位数字）",
        examples=["123456"]
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="密码（至少6个字符）",
        examples=["password123"]
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """验证手机号格式"""
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确')
        return v

    @field_validator('verification_code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证验证码格式"""
        if not re.match(r'^\d{6}$', v):
            raise ValueError('验证码必须为6位数字')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "zhangsan",
                    "phone": "13800138000",
                    "verification_code": "123456",
                    "password": "password123",
                    "email": "zhangsan@example.com"
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """Token响应"""

    access_token: str = Field(
        ...,
        description="访问令牌",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    refresh_token: str = Field(
        ...,
        description="刷新令牌",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    token_type: str = Field(
        default="bearer",
        description="令牌类型",
        examples=["bearer"]
    )
    expires_in: int = Field(
        ...,
        description="访问令牌过期时间（秒）",
        examples=[3600]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""

    refresh_token: str = Field(
        ...,
        description="刷新令牌",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
            ]
        }
    }


class LogoutRequest(BaseModel):
    """登出请求"""

    refresh_token: str = Field(
        ...,
        description="刷新令牌",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
                }
            ]
        }
    }


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="旧密码",
        examples=["oldpassword123"]
    )
    new_password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="新密码（至少6个字符）",
        examples=["newpassword123"]
    )

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str, info) -> str:
        """验证新密码不能与旧密码相同"""
        if 'old_password' in info.data and v == info.data['old_password']:
            raise ValueError('新密码不能与旧密码相同')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "old_password": "oldpassword123",
                    "new_password": "newpassword123"
                }
            ]
        }
    }


class UserResponse(BaseModel):
    """用户信息响应"""

    id: UUID
    username: str
    phone: str  # 手机号必填
    avatar: Optional[str]
    balance: float
    member_level: int
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    """注册响应"""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    """登录响应"""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
