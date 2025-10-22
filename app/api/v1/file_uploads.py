"""
文件上传API端点 - 实现架构文档 §5.2
"""
from fastapi import APIRouter, Depends, File, UploadFile, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.file_upload import (
    FileCheckRequest,
    FileCheckResponse,
    FileUploadResponse,
    MultipartInitRequest,
    MultipartInitResponse,
    ChunkUploadRequest,
    ChunkUploadResponse,
    MultipartCompleteRequest,
    MultipartCompleteResponse,
    MultipartAbortRequest,
    FileRetryResponse,
)
from app.services.file_upload_service import FileUploadService

router = APIRouter(prefix="/upload-tasks/{task_id}/files", tags=["File Uploads"])


@router.post("/check", response_model=FileCheckResponse)
async def check_files(
    task_id: UUID = Path(..., description="任务ID"),
    request: FileCheckRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    批量检查文件（秒传检测）

    根据架构文档 §六.阶段2

    Args:
        task_id: 任务ID
        request: 检查请求（包含文件MD5列表）
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        FileCheckResponse: 检查结果
    """
    service = FileUploadService(db)
    result = await service.check_files_exist(
        task_id=task_id,
        files=request.files,
        user_id=current_user.id
    )

    return FileCheckResponse(
        existing_files=result["existing_files"],
        new_files_count=result["new_files_count"],
        storage_saved=result["storage_saved"],
    )


@router.post("/{file_id}/upload", response_model=FileUploadResponse)
async def upload_file(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="任务文件ID"),
    file: UploadFile = File(..., description="上传的文件"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传单个文件（小文件直接上传）

    根据架构文档 §六.阶段3 - 小文件直接上传

    Args:
        task_id: 任务ID
        file_id: 任务文件ID
        file: 上传的文件
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        FileUploadResponse: 上传结果
    """
    service = FileUploadService(db)
    result = await service.upload_file(
        task_file_id=file_id,
        file=file,
        user_id=current_user.id
    )

    return FileUploadResponse(**result)


@router.put("/{file_id}/retry", response_model=FileRetryResponse)
async def retry_file_upload(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="任务文件ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    重试失败的文件

    Args:
        task_id: 任务ID
        file_id: 任务文件ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        FileRetryResponse: 重试结果
    """
    service = FileUploadService(db)
    result = await service.retry_file(
        task_file_id=file_id,
        user_id=current_user.id
    )

    return FileRetryResponse(**result)


# ==================== 分片上传相关端点 ====================

@router.post("/{file_id}/multipart/init", response_model=MultipartInitResponse)
async def init_multipart_upload(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="任务文件ID"),
    request: MultipartInitRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    初始化分片上传

    根据架构文档 §六.阶段3 - 大文件分片上传

    Args:
        task_id: 任务ID
        file_id: 任务文件ID
        request: 初始化请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        MultipartInitResponse: 初始化响应
    """
    # 确保 task_file_id 正确
    request.task_file_id = file_id

    service = FileUploadService(db)
    result = await service.init_multipart_upload(
        request=request,
        user_id=current_user.id
    )

    return MultipartInitResponse(**result)


@router.post("/{file_id}/multipart/upload", response_model=ChunkUploadResponse)
async def upload_chunk(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="任务文件ID"),
    chunk_index: int = Body(..., embed=True, description="分片索引（从1开始）"),
    chunk: UploadFile = File(..., description="分片数据"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    上传分片

    Args:
        task_id: 任务ID
        file_id: 任务文件ID
        chunk_index: 分片索引
        chunk: 分片数据
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ChunkUploadResponse: 上传响应
    """
    service = FileUploadService(db)

    # 读取分片数据
    chunk_data = await chunk.read()

    result = await service.upload_chunk(
        task_file_id=file_id,
        chunk_index=chunk_index,
        chunk_data=chunk_data,
        user_id=current_user.id
    )

    return ChunkUploadResponse(**result)


@router.post("/{file_id}/multipart/complete", response_model=MultipartCompleteResponse)
async def complete_multipart_upload(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="任务文件ID"),
    request: MultipartCompleteRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    完成分片上传

    Args:
        task_id: 任务ID
        file_id: 任务文件ID
        request: 完成请求（包含所有分片的ETag）
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        MultipartCompleteResponse: 完成响应
    """
    service = FileUploadService(db)
    result = await service.complete_multipart_upload(
        task_file_id=file_id,
        chunk_etags=request.chunk_etags,
        user_id=current_user.id
    )

    return MultipartCompleteResponse(**result)


@router.post("/{file_id}/multipart/abort", status_code=204)
async def abort_multipart_upload(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="任务文件ID"),
    request: MultipartAbortRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    中止分片上传

    Args:
        task_id: 任务ID
        file_id: 任务文件ID
        request: 中止请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        None: 成功中止返回 204 状态码
    """
    service = FileUploadService(db)
    await service.abort_multipart_upload(
        task_file_id=file_id,
        user_id=current_user.id,
        reason=request.reason
    )
