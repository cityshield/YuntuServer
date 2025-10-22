"""
盘符服务
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException, status

from app.models.drive import Drive
from app.models.team_member import TeamMember, TeamRole
from app.schemas.drive import DriveCreate, DriveUpdate


class DriveService:
    """盘符服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_drive(
        self, drive_data: DriveCreate, user_id: UUID
    ) -> Drive:
        """
        创建盘符

        Args:
            drive_data: 盘符数据
            user_id: 用户ID

        Returns:
            Drive: 创建的盘符对象

        Raises:
            HTTPException: 团队盘必须指定team_id或权限不足
        """
        # 如果是团队盘，需要验证team_id和权限
        if drive_data.is_team_drive:
            if not drive_data.team_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Team ID is required for team drive",
                )

            # 检查用户是否是团队管理员或所有者
            team_member_result = await self.db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == drive_data.team_id,
                    TeamMember.user_id == user_id,
                    TeamMember.role.in_([TeamRole.OWNER, TeamRole.ADMIN])
                )
            )
            team_member = team_member_result.scalar_one_or_none()
            if not team_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only team owner or admin can create team drive",
                )

        # 创建盘符
        drive = Drive(
            name=drive_data.name,
            icon=drive_data.icon,
            description=drive_data.description,
            total_size=drive_data.total_size,
            is_team_drive=drive_data.is_team_drive,
            user_id=None if drive_data.is_team_drive else user_id,
            team_id=drive_data.team_id if drive_data.is_team_drive else None,
        )

        self.db.add(drive)
        await self.db.commit()
        await self.db.refresh(drive)

        return drive

    async def get_drive_by_id(self, drive_id: UUID, user_id: UUID) -> Optional[Drive]:
        """
        根据ID获取盘符

        Args:
            drive_id: 盘符ID
            user_id: 用户ID

        Returns:
            Optional[Drive]: 盘符对象，不存在或无权限则返回None
        """
        # 查询盘符
        result = await self.db.execute(select(Drive).where(Drive.id == drive_id))
        drive = result.scalar_one_or_none()

        if not drive:
            return None

        # 检查权限：个人盘只能访问自己的，团队盘需要是团队成员
        if not drive.is_team_drive:
            if drive.user_id != user_id:
                return None
        else:
            # 检查是否是团队成员
            team_member_result = await self.db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == drive.team_id,
                    TeamMember.user_id == user_id,
                )
            )
            team_member = team_member_result.scalar_one_or_none()
            if not team_member:
                return None

        return drive

    async def get_user_drives(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Drive], int]:
        """
        获取用户可访问的所有盘符（个人盘 + 团队盘）

        Args:
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            Tuple[List[Drive], int]: (盘符列表, 总数)
        """
        # 查询用户所属的团队
        team_ids_result = await self.db.execute(
            select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        )
        team_ids = [row[0] for row in team_ids_result.all()]

        # 查询总数：个人盘 + 团队盘
        count_query = select(func.count(Drive.id)).where(
            or_(
                Drive.user_id == user_id,  # 个人盘
                Drive.team_id.in_(team_ids) if team_ids else False  # 团队盘
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询盘符列表
        query = (
            select(Drive)
            .where(
                or_(
                    Drive.user_id == user_id,
                    Drive.team_id.in_(team_ids) if team_ids else False
                )
            )
            .order_by(Drive.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        drives = result.scalars().all()

        return list(drives), total

    async def update_drive(
        self, drive_id: UUID, user_id: UUID, drive_update: DriveUpdate
    ) -> Drive:
        """
        更新盘符信息

        Args:
            drive_id: 盘符ID
            user_id: 用户ID
            drive_update: 更新数据

        Returns:
            Drive: 更新后的盘符对象

        Raises:
            HTTPException: 盘符不存在或权限不足
        """
        # 查询盘符
        drive = await self.get_drive_by_id(drive_id, user_id)
        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drive not found or access denied",
            )

        # 检查权限：团队盘需要管理员权限
        if drive.is_team_drive:
            team_member_result = await self.db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == drive.team_id,
                    TeamMember.user_id == user_id,
                    TeamMember.role.in_([TeamRole.OWNER, TeamRole.ADMIN])
                )
            )
            team_member = team_member_result.scalar_one_or_none()
            if not team_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only team owner or admin can update team drive",
                )

        # 更新字段
        update_data = drive_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(drive, field, value)

        await self.db.commit()
        await self.db.refresh(drive)

        return drive

    async def delete_drive(self, drive_id: UUID, user_id: UUID) -> None:
        """
        删除盘符

        Args:
            drive_id: 盘符ID
            user_id: 用户ID

        Raises:
            HTTPException: 盘符不存在或权限不足
        """
        # 查询盘符
        drive = await self.get_drive_by_id(drive_id, user_id)
        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drive not found or access denied",
            )

        # 检查权限：团队盘需要所有者权限
        if drive.is_team_drive:
            team_member_result = await self.db.execute(
                select(TeamMember).where(
                    TeamMember.team_id == drive.team_id,
                    TeamMember.user_id == user_id,
                    TeamMember.role == TeamRole.OWNER
                )
            )
            team_member = team_member_result.scalar_one_or_none()
            if not team_member:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only team owner can delete team drive",
                )

        # 删除盘符（级联删除文件夹和文件）
        await self.db.delete(drive)
        await self.db.commit()

    async def get_drive_stats(self, user_id: UUID) -> dict:
        """
        获取用户盘符统计信息

        Args:
            user_id: 用户ID

        Returns:
            dict: 统计信息
        """
        drives, total = await self.get_user_drives(user_id, skip=0, limit=1000)

        # 计算统计数据
        personal_drives = sum(1 for d in drives if not d.is_team_drive)
        team_drives = sum(1 for d in drives if d.is_team_drive)
        total_size = sum(d.total_size for d in drives if d.total_size)
        used_size = sum(d.used_size for d in drives)
        available_size = total_size - used_size if total_size else -1
        usage_percentage = (used_size / total_size * 100) if total_size and total_size > 0 else 0.0

        return {
            "total_drives": total,
            "personal_drives": personal_drives,
            "team_drives": team_drives,
            "total_size": total_size,
            "used_size": used_size,
            "available_size": available_size,
            "usage_percentage": usage_percentage,
        }
