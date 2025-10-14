"""
任务相关API端点
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskListResponse,
    TaskLogsResponse,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建任务

    Args:
        task_data: 任务数据
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskResponse: 创建的任务信息
    """
    task_service = TaskService(db)
    task = await task_service.create_task(
        user_id=current_user.id, task_data=task_data
    )
    return task


@router.get("/", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[int] = Query(
        None,
        ge=0,
        le=7,
        description="任务状态 0:Draft, 1:Pending, 2:Queued, 3:Rendering, 4:Paused, 5:Completed, 6:Failed, 7:Cancelled",
    ),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务列表

    Args:
        status: 任务状态过滤
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskListResponse: 任务列表
    """
    task_service = TaskService(db)
    tasks, total = await task_service.get_tasks(
        user_id=current_user.id, status=status, skip=skip, limit=limit
    )
    return {
        "tasks": tasks,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_detail(
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
        TaskResponse: 任务详情
    """
    task_service = TaskService(db)
    task = await task_service.get_task_by_id(task_id=task_id, user_id=current_user.id)
    return task


@router.put("/{task_id}/pause", response_model=TaskResponse)
async def pause_task(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    暂停任务

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskResponse: 更新后的任务信息
    """
    task_service = TaskService(db)
    task = await task_service.pause_task(task_id=task_id, user_id=current_user.id)
    return task


@router.put("/{task_id}/resume", response_model=TaskResponse)
async def resume_task(
    task_id: UUID = Path(..., description="任务ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    恢复任务

    Args:
        task_id: 任务ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskResponse: 更新后的任务信息
    """
    task_service = TaskService(db)
    task = await task_service.resume_task(task_id=task_id, user_id=current_user.id)
    return task


@router.put("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
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
        TaskResponse: 更新后的任务信息
    """
    task_service = TaskService(db)
    task = await task_service.cancel_task(task_id=task_id, user_id=current_user.id)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
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
        None: 成功删除返回204状态码
    """
    task_service = TaskService(db)
    await task_service.delete_task(task_id=task_id, user_id=current_user.id)
    return None


@router.get("/{task_id}/logs", response_model=TaskLogsResponse)
async def get_task_logs(
    task_id: UUID = Path(..., description="任务ID"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务日志

    Args:
        task_id: 任务ID
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        TaskLogsResponse: 任务日志列表
    """
    task_service = TaskService(db)
    logs, total = await task_service.get_task_logs(
        task_id=task_id, user_id=current_user.id, skip=skip, limit=limit
    )
    return {
        "logs": logs,
        "total": total,
    }
