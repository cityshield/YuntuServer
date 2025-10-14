"""
通用响应模型
"""
from typing import TypeVar, Generic, Optional, Any, List
from pydantic import BaseModel, Field


# 泛型类型变量
T = TypeVar('T')


class Response(BaseModel, Generic[T]):
    """通用响应模型"""

    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="Success", description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 200,
                    "message": "Success",
                    "data": {"id": "123e4567-e89b-12d3-a456-426614174000"}
                }
            ]
        }
    }


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    code: int = Field(default=200, description="响应状态码")
    message: str = Field(default="Success", description="响应消息")
    data: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, ge=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页记录数")
    total_pages: int = Field(default=0, ge=0, description="总页数")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 200,
                    "message": "Success",
                    "data": [
                        {"id": "123e4567-e89b-12d3-a456-426614174000", "name": "Item 1"},
                        {"id": "223e4567-e89b-12d3-a456-426614174001", "name": "Item 2"}
                    ],
                    "total": 100,
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 10
                }
            ]
        }
    }


class MessageResponse(BaseModel):
    """消息响应模型"""

    code: int = Field(default=200, description="响应状态码")
    message: str = Field(description="响应消息")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 200,
                    "message": "操作成功"
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """错误响应模型"""

    code: int = Field(description="错误状态码")
    message: str = Field(description="错误消息")
    detail: Optional[Any] = Field(default=None, description="错误详情")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 400,
                    "message": "参数错误",
                    "detail": {"field": "username", "error": "用户名已存在"}
                }
            ]
        }
    }
