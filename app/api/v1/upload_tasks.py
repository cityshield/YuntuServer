"""
上传任务管理API端点 - 实现架构文档 §5.1
"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.upload_task import TaskStatus
from app.schemas.upload_task import (
    UploadTaskCreate,
    UploadTaskUpdate,
    UploadTaskResponse,
    UploadTaskListResponse,
    TaskFileListResponse,
    TaskFileResponse,
    UploadProgressResponse,
    StorageManifest,
    FileCompleteRequest,
)
from app.schemas.file_upload import DownloadLinkResponse, ArchiveRequest, ArchiveResponse
from app.services.upload_task_service import UploadTaskService
from app.services.batch_download_service import BatchDownloadService

router = APIRouter(prefix="/upload-tasks", tags=["Upload Tasks"])


@router.post("", response_model=UploadTaskResponse, status_code=201)
async def create_upload_task(
    task_data: UploadTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建上传任务

    根据架构文档 §六.阶段1

    Args:
        task_data: 任务数据（包含 upload_manifest）
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UploadTaskResponse: 创建的任务信息
    """
    service = UploadTaskService(db)
    task = await service.create_task(task_data.upload_manifest, current_user.id)
    return task


@router.get("", response_model=UploadTaskListResponse)
async def get_upload_tasks(
    status: Optional[TaskStatus] = Query(None, description="任务状态筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务列表

    Args:
        status: 状态筛选（可选）
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UploadTaskListResponse: 任务列表
    """
    service = UploadTaskService(db)
    tasks, total = await service.list_tasks(
        user_id=current_user.id,
        status_filter=status,
        skip=skip,
        limit=limit
    )
    return {
        "tasks": tasks,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{task_id}", response_model=UploadTaskResponse)
async def get_upload_task(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务详情

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UploadTaskResponse: 任务信息
    """
    from fastapi import HTTPException, status as http_status

    service = UploadTaskService(db)
    task = await service.get_task(task_id, current_user.id)

    if not task:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    return task


@router.get("/{task_id}/files", response_model=TaskFileListResponse)
async def get_task_files(
    task_id: UUID = Path(..., description="任务ID"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务文件列表

    Args:
        task_id: 任务ID
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskFileListResponse: 文件列表
    """
    service = UploadTaskService(db)
    files, total = await service.get_task_files(
        task_id=task_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return {
        "files": files,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{task_id}/progress", response_model=UploadProgressResponse)
async def get_upload_progress(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取上传进度

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UploadProgressResponse: 进度信息
    """
    from fastapi import HTTPException, status as http_status

    service = UploadTaskService(db)
    task = await service.get_task(task_id, current_user.id)

    if not task:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    return UploadProgressResponse(
        task_id=task.id,
        status=task.status,
        progress_percentage=task.progress_percentage,
        size_progress_percentage=task.size_progress_percentage,
        uploaded_files=task.uploaded_files,
        total_files=task.total_files,
        uploaded_size=task.uploaded_size,
        total_size=task.total_size,
        remaining_files=task.remaining_files,
        remaining_size=task.remaining_size,
        updated_at=task.updated_at or task.created_at,
    )


@router.post("/{task_id}/files/{file_id}/complete", response_model=TaskFileResponse)
async def mark_file_complete(
    task_id: UUID = Path(..., description="任务ID"),
    file_id: UUID = Path(..., description="文件ID"),
    request: FileCompleteRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    标记文件上传完成

    客户端在完成 OSS 直传后调用此接口通知服务器
    服务器会更新 TaskFile 状态并创建 File 数据库记录

    Args:
        task_id: 任务ID
        file_id: 文件ID (TaskFile.id)
        request: 文件完成信息
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskFileResponse: 更新后的文件信息
    """
    service = UploadTaskService(db)
    task_file = await service.mark_file_completed(
        task_id=task_id,
        file_id=file_id,
        user_id=current_user.id,
        oss_key=request.oss_key,
        oss_url=request.oss_url,
        md5=request.md5,
        file_size=request.file_size,
    )
    return task_file


@router.put("/{task_id}/cancel", response_model=UploadTaskResponse)
async def cancel_upload_task(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    取消任务

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        UploadTaskResponse: 更新后的任务信息
    """
    service = UploadTaskService(db)
    task = await service.cancel_task(task_id, current_user.id)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_upload_task(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除任务

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        None: 成功删除返回 204 状态码
    """
    from fastapi import HTTPException, status as http_status

    service = UploadTaskService(db)
    task = await service.get_task(task_id, current_user.id)

    if not task:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Task not found or access denied"
        )

    await db.delete(task)
    await db.commit()


@router.post("/{task_id}/export-manifest", response_model=StorageManifest)
async def export_storage_manifest(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    导出存储描述文件

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        StorageManifest: 存储描述文件
    """
    service = UploadTaskService(db)
    manifest = await service.generate_storage_manifest(task_id)
    return manifest


# ==================== 批量下载相关端点 ====================

@router.get("/{task_id}/download", response_model=DownloadLinkResponse)
async def get_download_links(
    task_id: UUID = Path(..., description="任务ID"),
    expires_in: int = Query(3600, ge=60, le=86400, description="过期时间（秒）"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    生成批量下载链接

    Args:
        task_id: 任务ID
        expires_in: 过期时间（秒）
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        DownloadLinkResponse: 下载链接信息
    """
    service = BatchDownloadService(db)
    result = await service.generate_download_links(
        task_id=task_id,
        user_id=current_user.id,
        expires_in=expires_in
    )

    return DownloadLinkResponse(
        download_url=result.get("download_url", ""),
        expires_in=expires_in,
        file_count=result["file_count"],
        total_size=result["total_size"],
    )


@router.post("/{task_id}/archive", response_model=ArchiveResponse)
async def create_archive(
    task_id: UUID = Path(..., description="任务ID"),
    request: ArchiveRequest = ...,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建打包任务（ZIP 格式）

    Args:
        task_id: 任务ID
        request: 打包请求
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        ArchiveResponse: 打包任务信息
    """
    service = BatchDownloadService(db)
    result = await service.create_archive(
        task_id=task_id,
        user_id=current_user.id,
        archive_name=request.archive_name,
        format=request.format
    )

    return ArchiveResponse(
        archive_id=result["archive_id"],
        status=result["status"],
        download_url=result.get("download_url"),
        expires_at=result.get("expires_at"),
    )
