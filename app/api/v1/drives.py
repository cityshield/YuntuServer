"""
盘符管理API端点
"""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.drive import (
    DriveCreate,
    DriveUpdate,
    DriveResponse,
    DriveListResponse,
    DriveStatsResponse,
)
from app.services.drive_service import DriveService

router = APIRouter(prefix="/drives", tags=["Drives"])


@router.post("", response_model=DriveResponse, status_code=201)
async def create_drive(
    drive_data: DriveCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    创建盘符

    Args:
        drive_data: 盘符数据
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        DriveResponse: 创建的盘符信息
    """
    drive_service = DriveService(db)
    drive = await drive_service.create_drive(drive_data, current_user.id)
    return drive


@router.get("", response_model=DriveListResponse)
async def get_drives(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前用户可访问的所有盘符

    Args:
        skip: 跳过记录数
        limit: 返回记录数
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        DriveListResponse: 盘符列表
    """
    drive_service = DriveService(db)
    drives, total = await drive_service.get_user_drives(
        user_id=current_user.id, skip=skip, limit=limit
    )
    return {
        "drives": drives,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/stats", response_model=DriveStatsResponse)
async def get_drive_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取盘符统计信息

    Args:
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        DriveStatsResponse: 统计信息
    """
    drive_service = DriveService(db)
    stats = await drive_service.get_drive_stats(current_user.id)
    return stats


@router.get("/{drive_id}", response_model=DriveResponse)
async def get_drive(
    drive_id: UUID = Path(..., description="盘符ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取盘符详情

    Args:
        drive_id: 盘符ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        DriveResponse: 盘符信息
    """
    from fastapi import HTTPException, status

    drive_service = DriveService(db)
    drive = await drive_service.get_drive_by_id(drive_id, current_user.id)
    if not drive:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drive not found or access denied",
        )
    return drive


@router.put("/{drive_id}", response_model=DriveResponse)
async def update_drive(
    drive_update: DriveUpdate,
    drive_id: UUID = Path(..., description="盘符ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新盘符信息

    Args:
        drive_id: 盘符ID
        drive_update: 更新数据
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        DriveResponse: 更新后的盘符信息
    """
    drive_service = DriveService(db)
    drive = await drive_service.update_drive(drive_id, current_user.id, drive_update)
    return drive


@router.delete("/{drive_id}", status_code=204)
async def delete_drive(
    drive_id: UUID = Path(..., description="盘符ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    删除盘符

    Args:
        drive_id: 盘符ID
        current_user: 当前登录用户
        db: 数据库会话

    Returns:
        None: 成功删除返回 204 状态码
    """
    drive_service = DriveService(db)
    await drive_service.delete_drive(drive_id, current_user.id)
