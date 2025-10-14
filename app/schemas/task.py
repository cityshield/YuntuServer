"""
任务相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from decimal import Decimal
from enum import IntEnum


class TaskStatus(IntEnum):
    """任务状态枚举"""
    DRAFT = 0
    PENDING = 1
    QUEUED = 2
    RENDERING = 3
    PAUSED = 4
    COMPLETED = 5
    FAILED = 6
    CANCELLED = 7


class TaskPriority(IntEnum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskBase(BaseModel):
    """任务基础模型"""

    task_name: str = Field(
        ...,
        max_length=200,
        description="任务名称",
        examples=["场景渲染任务001"]
    )
    scene_file: Optional[str] = Field(
        None,
        max_length=500,
        description="场景文件路径",
        examples=["/path/to/scene.ma"]
    )
    maya_version: Optional[str] = Field(
        None,
        max_length=20,
        description="Maya版本",
        examples=["2023"]
    )
    renderer: Optional[str] = Field(
        None,
        max_length=50,
        description="渲染器",
        examples=["Arnold", "V-Ray", "Redshift"]
    )
    priority: int = Field(
        default=1,
        ge=0,
        le=3,
        description="优先级 (0:Low, 1:Normal, 2:High, 3:Urgent)",
        examples=[1]
    )
    start_frame: Optional[int] = Field(
        None,
        description="起始帧",
        examples=[1]
    )
    end_frame: Optional[int] = Field(
        None,
        description="结束帧",
        examples=[100]
    )
    frame_step: int = Field(
        default=1,
        ge=1,
        description="帧步长",
        examples=[1]
    )
    width: Optional[int] = Field(
        None,
        gt=0,
        description="渲染宽度",
        examples=[1920]
    )
    height: Optional[int] = Field(
        None,
        gt=0,
        description="渲染高度",
        examples=[1080]
    )
    output_path: Optional[str] = Field(
        None,
        max_length=500,
        description="输出路径",
        examples=["/output/render/"]
    )
    output_format: Optional[str] = Field(
        None,
        max_length=20,
        description="输出格式",
        examples=["png", "exr", "jpg"]
    )

    @field_validator('end_frame')
    @classmethod
    def validate_frame_range(cls, v: Optional[int], info) -> Optional[int]:
        """验证帧范围"""
        if v is not None and 'start_frame' in info.data:
            start_frame = info.data['start_frame']
            if start_frame is not None and v < start_frame:
                raise ValueError('结束帧必须大于等于起始帧')
        return v


class TaskCreate(TaskBase):
    """创建任务模型"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_name": "场景渲染任务001",
                    "scene_file": "/path/to/scene.ma",
                    "maya_version": "2023",
                    "renderer": "Arnold",
                    "priority": 1,
                    "start_frame": 1,
                    "end_frame": 100,
                    "frame_step": 1,
                    "width": 1920,
                    "height": 1080,
                    "output_path": "/output/render/",
                    "output_format": "png"
                }
            ]
        }
    }


class TaskUpdate(BaseModel):
    """更新任务模型"""

    task_name: Optional[str] = Field(
        None,
        max_length=200,
        description="任务名称",
        examples=["场景渲染任务001"]
    )
    scene_file: Optional[str] = Field(
        None,
        max_length=500,
        description="场景文件路径",
        examples=["/path/to/scene.ma"]
    )
    maya_version: Optional[str] = Field(
        None,
        max_length=20,
        description="Maya版本",
        examples=["2023"]
    )
    renderer: Optional[str] = Field(
        None,
        max_length=50,
        description="渲染器",
        examples=["Arnold"]
    )
    priority: Optional[int] = Field(
        None,
        ge=0,
        le=3,
        description="优先级",
        examples=[1]
    )
    start_frame: Optional[int] = Field(
        None,
        description="起始帧",
        examples=[1]
    )
    end_frame: Optional[int] = Field(
        None,
        description="结束帧",
        examples=[100]
    )
    frame_step: Optional[int] = Field(
        None,
        ge=1,
        description="帧步长",
        examples=[1]
    )
    width: Optional[int] = Field(
        None,
        gt=0,
        description="宽度",
        examples=[1920]
    )
    height: Optional[int] = Field(
        None,
        gt=0,
        description="高度",
        examples=[1080]
    )
    output_path: Optional[str] = Field(
        None,
        max_length=500,
        description="输出路径",
        examples=["/output/render/"]
    )
    output_format: Optional[str] = Field(
        None,
        max_length=20,
        description="输出格式",
        examples=["png"]
    )


class TaskStatusUpdate(BaseModel):
    """任务状态更新模型"""

    status: int = Field(
        ...,
        ge=0,
        le=7,
        description="状态 (0:Draft, 1:Pending, 2:Queued, 3:Rendering, 4:Paused, 5:Completed, 6:Failed, 7:Cancelled)",
        examples=[3]
    )
    progress: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="进度百分比",
        examples=[50]
    )
    error_message: Optional[str] = Field(
        None,
        description="错误消息（当状态为Failed时）",
        examples=["渲染失败：内存不足"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": 3,
                    "progress": 50
                }
            ]
        }
    }


class TaskResponse(BaseModel):
    """任务响应模型"""

    id: UUID
    user_id: UUID
    task_name: str
    scene_file: Optional[str]
    maya_version: Optional[str]
    renderer: Optional[str]
    status: int = Field(..., description="状态 (0:Draft, 1:Pending, 2:Queued, 3:Rendering, 4:Paused, 5:Completed, 6:Failed, 7:Cancelled)")
    priority: int
    progress: int = Field(..., ge=0, le=100, description="进度百分比")
    start_frame: Optional[int]
    end_frame: Optional[int]
    frame_step: int
    width: Optional[int]
    height: Optional[int]
    output_path: Optional[str]
    output_format: Optional[str]
    estimated_cost: Optional[Decimal] = Field(None, description="预估费用")
    actual_cost: Optional[Decimal] = Field(None, description="实际费用")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """任务列表响应模型"""

    tasks: List[TaskResponse]
    total: int
    skip: int
    limit: int


class TaskLogBase(BaseModel):
    """任务日志基础模型"""

    log_level: str = Field(
        ...,
        max_length=20,
        description="日志级别 (INFO, WARNING, ERROR)",
        examples=["INFO"]
    )
    message: str = Field(
        ...,
        description="日志消息",
        examples=["开始渲染第1帧"]
    )


class TaskLogCreate(TaskLogBase):
    """创建任务日志模型"""

    task_id: UUID = Field(
        ...,
        description="任务ID",
        examples=["123e4567-e89b-12d3-a456-426614174000"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "123e4567-e89b-12d3-a456-426614174000",
                    "log_level": "INFO",
                    "message": "开始渲染第1帧"
                }
            ]
        }
    }


class TaskLogResponse(TaskLogBase):
    """任务日志响应模型"""

    id: int
    task_id: UUID
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class TaskLogsResponse(BaseModel):
    """任务日志列表响应模型"""

    logs: List[TaskLogResponse]
    total: int
