"""
上传任务相关的Pydantic模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.models.upload_task import TaskStatus
from app.models.task_file import FileUploadStatus


# ==================== 上传描述文件（客户端 → 服务端） ====================

class UploadManifestFile(BaseModel):
    """上传描述文件中的单个文件信息"""

    index: int = Field(..., description="文件索引")
    local_path: str = Field(..., max_length=1024, description="客户端本地路径")
    target_folder_path: str = Field(..., max_length=1024, description="目标文件夹路径")
    file_name: str = Field(..., max_length=255, description="文件名")
    file_size: int = Field(..., ge=0, description="文件大小（字节）")
    md5: Optional[str] = Field(None, max_length=32, description="MD5哈希值")
    mime_type: Optional[str] = Field(None, max_length=100, description="MIME类型")
    modified_time: Optional[datetime] = Field(None, description="文件修改时间")


class ClientInfo(BaseModel):
    """客户端信息"""

    platform: str = Field(..., description="客户端平台")
    version: str = Field(..., description="客户端版本")
    ip: Optional[str] = Field(None, description="客户端IP地址")


class UploadManifest(BaseModel):
    """上传描述文件（客户端提交）"""

    task_name: str = Field(..., max_length=255, description="任务名称")
    drive_id: UUID = Field(..., description="盘符ID")
    priority: int = Field(default=5, ge=0, le=10, description="优先级 0-10")
    total_files: int = Field(..., ge=0, description="总文件数")
    total_size: int = Field(..., ge=0, description="总大小（字节）")
    client_info: Optional[ClientInfo] = Field(None, description="客户端信息")
    files: List[UploadManifestFile] = Field(..., description="文件列表")


# ==================== 存储描述文件（服务端生成） ====================

class StorageManifestFile(BaseModel):
    """存储描述文件中的单个文件信息"""

    file_id: UUID = Field(..., description="文件ID")
    task_file_id: UUID = Field(..., description="任务文件ID")
    file_name: str = Field(..., description="文件名")
    local_path: str = Field(..., description="客户端本地路径")
    virtual_path: str = Field(..., description="虚拟路径")
    folder_id: Optional[UUID] = Field(None, description="文件夹ID")
    oss_key: str = Field(..., description="OSS对象键")
    oss_url: str = Field(..., description="OSS访问URL")
    file_size: int = Field(..., description="文件大小")
    md5: str = Field(..., description="MD5哈希值")
    upload_status: str = Field(..., description="上传状态")
    is_duplicated: bool = Field(..., description="是否秒传")
    upload_duration: Optional[float] = Field(None, description="上传耗时（秒）")


class StorageManifestSummary(BaseModel):
    """存储描述文件摘要"""

    total_files: int = Field(..., description="总文件数")
    uploaded_files: int = Field(..., description="已上传文件数")
    failed_files: int = Field(..., description="失败文件数")
    skipped_files: int = Field(..., description="跳过文件数（秒传）")
    total_size: int = Field(..., description="总大小")
    storage_saved: int = Field(..., description="节省的存储空间（秒传）")


class StorageManifest(BaseModel):
    """存储描述文件（服务端生成）"""

    task_id: UUID = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    user_id: UUID = Field(..., description="用户ID")
    drive_id: UUID = Field(..., description="盘符ID")
    drive_name: str = Field(..., description="盘符名称")
    status: TaskStatus = Field(..., description="任务状态")
    summary: StorageManifestSummary = Field(..., description="摘要信息")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    files: List[StorageManifestFile] = Field(default_factory=list, description="文件列表")
    mappings: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="映射关系（local_to_oss, local_to_virtual, oss_to_file_id）"
    )


# ==================== 任务相关 Schemas ====================

class UploadTaskCreate(BaseModel):
    """创建上传任务请求"""

    upload_manifest: UploadManifest = Field(..., description="上传描述文件")


class UploadTaskUpdate(BaseModel):
    """更新上传任务请求"""

    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[int] = Field(None, ge=0, le=10, description="优先级")


class TaskFileResponse(BaseModel):
    """任务文件响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    file_id: Optional[UUID]
    local_path: str
    target_folder_path: str
    file_name: str
    file_size: int
    md5: Optional[str]
    mime_type: Optional[str]
    status: FileUploadStatus
    upload_progress: float
    oss_key: Optional[str]
    oss_url: Optional[str]
    is_duplicated: bool
    duplicated_from: Optional[UUID]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    # 计算属性
    virtual_path: str
    is_completed: bool
    is_failed: bool
    can_retry: bool


class UploadTaskResponse(BaseModel):
    """上传任务响应模型"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    drive_id: UUID
    task_name: str
    status: TaskStatus
    priority: int
    total_files: int
    uploaded_files: int
    total_size: int
    uploaded_size: int
    upload_manifest: Optional[Dict[str, Any]]
    storage_manifest: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    # 计算属性
    progress_percentage: float
    size_progress_percentage: float
    remaining_files: int
    remaining_size: int
    is_completed: bool
    is_in_progress: bool


class UploadTaskListResponse(BaseModel):
    """上传任务列表响应模型"""

    tasks: List[UploadTaskResponse]
    total: int = Field(description="总数")
    skip: int = Field(description="跳过的记录数")
    limit: int = Field(description="返回的记录数")


class TaskFileListResponse(BaseModel):
    """任务文件列表响应模型"""

    files: List[TaskFileResponse]
    total: int = Field(description="总数")
    skip: int = Field(description="跳过的记录数")
    limit: int = Field(description="返回的记录数")


class UploadProgressResponse(BaseModel):
    """上传进度响应模型"""

    task_id: UUID
    status: TaskStatus
    progress_percentage: float
    size_progress_percentage: float
    uploaded_files: int
    total_files: int
    uploaded_size: int
    total_size: int
    remaining_files: int
    remaining_size: int
    updated_at: datetime
