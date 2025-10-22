"""
盘符相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class DriveBase(BaseModel):
    """盘符基础模型"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="盘符名称",
        examples=["C", "D", "项目盘"]
    )
    icon: Optional[str] = Field(
        None,
        max_length=50,
        description="图标（emoji 或图标类名）",
        examples=["💾", "📁"]
    )
    description: Optional[str] = Field(
        None,
        max_length=255,
        description="描述",
        examples=["我的文档盘"]
    )
    total_size: Optional[int] = Field(
        None,
        ge=0,
        description="总容量限制（字节），NULL 表示无限制",
        examples=[107374182400]  # 100GB
    )


class DriveCreate(DriveBase):
    """创建盘符模型"""

    is_team_drive: bool = Field(
        default=False,
        description="是否为团队盘"
    )
    team_id: Optional[UUID] = Field(
        None,
        description="团队ID（团队盘必填）"
    )


class DriveUpdate(BaseModel):
    """更新盘符模型"""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="盘符名称"
    )
    icon: Optional[str] = Field(
        None,
        max_length=50,
        description="图标"
    )
    description: Optional[str] = Field(
        None,
        max_length=255,
        description="描述"
    )
    total_size: Optional[int] = Field(
        None,
        ge=0,
        description="总容量限制（字节）"
    )
    is_active: Optional[bool] = Field(
        None,
        description="是否启用"
    )


class DriveResponse(BaseModel):
    """盘符响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    icon: Optional[str]
    description: Optional[str]
    total_size: Optional[int]
    used_size: int
    user_id: Optional[UUID]
    team_id: Optional[UUID]
    is_team_drive: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # 计算属性
    usage_percentage: float
    available_size: int


class DriveListResponse(BaseModel):
    """盘符列表响应模型"""

    drives: list[DriveResponse]
    total: int = Field(description="总数")
    skip: int = Field(description="跳过的记录数")
    limit: int = Field(description="返回的记录数")


class DriveStatsResponse(BaseModel):
    """盘符统计响应模型"""

    total_drives: int = Field(description="总盘符数")
    personal_drives: int = Field(description="个人盘符数")
    team_drives: int = Field(description="团队盘符数")
    total_size: int = Field(description="总容量")
    used_size: int = Field(description="已用容量")
    available_size: int = Field(description="可用容量")
    usage_percentage: float = Field(description="使用率")
