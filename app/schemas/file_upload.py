"""
文件上传相关的Pydantic模型
"""
from typing import List, Optional, Dict
from uuid import UUID
from pydantic import BaseModel, Field


# ==================== 秒传检查 ====================

class FileCheckItem(BaseModel):
    """单个文件检查项"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    md5: str = Field(..., max_length=32, description="文件MD5")
    file_size: int = Field(..., ge=0, description="文件大小")


class FileCheckRequest(BaseModel):
    """批量检查文件请求"""

    files: List[FileCheckItem] = Field(..., description="待检查的文件列表")


class ExistingFileInfo(BaseModel):
    """已存在的文件信息"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    md5: str = Field(..., description="MD5")
    existing_file_id: UUID = Field(..., description="已存在的文件ID")
    oss_key: str = Field(..., description="OSS对象键")
    oss_url: str = Field(..., description="OSS访问URL")
    file_size: int = Field(..., description="文件大小")


class FileCheckResponse(BaseModel):
    """批量检查文件响应"""

    existing_files: List[ExistingFileInfo] = Field(default_factory=list, description="已存在的文件列表")
    new_files_count: int = Field(..., description="需要上传的新文件数量")
    storage_saved: int = Field(..., description="节省的存储空间（字节）")


# ==================== 文件上传 ====================

class FileUploadResponse(BaseModel):
    """文件上传响应"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    file_id: UUID = Field(..., description="文件ID")
    oss_key: str = Field(..., description="OSS对象键")
    oss_url: str = Field(..., description="OSS访问URL")
    file_size: int = Field(..., description="文件大小")
    md5: str = Field(..., description="MD5哈希值")
    is_duplicated: bool = Field(..., description="是否秒传")
    upload_duration: float = Field(..., description="上传耗时（秒）")


# ==================== 分片上传 ====================

class MultipartInitRequest(BaseModel):
    """初始化分片上传请求"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    file_size: int = Field(..., ge=0, description="文件总大小")
    file_name: str = Field(..., max_length=255, description="文件名")
    mime_type: Optional[str] = Field(None, max_length=100, description="MIME类型")


class MultipartInitResponse(BaseModel):
    """初始化分片上传响应"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    upload_id: str = Field(..., description="OSS上传ID")
    chunk_size: int = Field(..., description="分片大小（字节）")
    total_chunks: int = Field(..., description="总分片数")


class ChunkUploadRequest(BaseModel):
    """上传分片请求（仅元数据，实际数据通过 FormData 上传）"""

    chunk_index: int = Field(..., ge=1, description="分片索引（从1开始）")


class ChunkUploadResponse(BaseModel):
    """上传分片响应"""

    chunk_index: int = Field(..., description="分片索引")
    chunk_etag: str = Field(..., description="分片ETag")
    uploaded_chunks: int = Field(..., description="已上传分片数")
    total_chunks: int = Field(..., description="总分片数")
    progress_percentage: float = Field(..., description="进度百分比")


class MultipartCompleteRequest(BaseModel):
    """完成分片上传请求"""

    chunk_etags: Dict[int, str] = Field(..., description="分片ETag映射（chunk_index: etag）")


class MultipartCompleteResponse(BaseModel):
    """完成分片上传响应"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    file_id: UUID = Field(..., description="文件ID")
    oss_key: str = Field(..., description="OSS对象键")
    oss_url: str = Field(..., description="OSS访问URL")
    file_size: int = Field(..., description="文件大小")
    md5: str = Field(..., description="MD5哈希值")
    is_duplicated: bool = Field(..., description="是否秒传")
    upload_duration: float = Field(..., description="上传耗时（秒）")


class MultipartAbortRequest(BaseModel):
    """中止分片上传请求"""

    reason: Optional[str] = Field(None, max_length=500, description="中止原因")


# ==================== 文件重试 ====================

class FileRetryResponse(BaseModel):
    """文件重试响应"""

    task_file_id: UUID = Field(..., description="任务文件ID")
    status: str = Field(..., description="新状态")
    retry_count: int = Field(..., description="重试次数")
    message: str = Field(..., description="提示信息")


# ==================== 批量下载 ====================

class DownloadLinkResponse(BaseModel):
    """下载链接响应"""

    download_url: str = Field(..., description="下载链接")
    expires_in: int = Field(..., description="过期时间（秒）")
    file_count: int = Field(..., description="文件数量")
    total_size: int = Field(..., description="总大小（字节）")


class ArchiveRequest(BaseModel):
    """创建打包任务请求"""

    format: str = Field(default="zip", description="打包格式（zip）")
    archive_name: Optional[str] = Field(None, max_length=255, description="压缩包名称")


class ArchiveResponse(BaseModel):
    """创建打包任务响应"""

    archive_id: UUID = Field(..., description="打包任务ID")
    status: str = Field(..., description="打包状态")
    download_url: Optional[str] = Field(None, description="下载链接（完成后可用）")
    expires_at: Optional[str] = Field(None, description="过期时间")
