"""
任务服务
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from app.models.task import Task, TaskLog
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.billing_service import BillingService


class TaskService:
    """任务服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.billing_service = BillingService(db)

    async def create_task(self, user_id: UUID, task_data: TaskCreate) -> Task:
        """
        创建任务

        Args:
            user_id: 用户ID
            task_data: 任务数据

        Returns:
            Task: 任务对象
        """
        # 创建任务对象
        task = Task(
            user_id=user_id,
            **task_data.model_dump(),
            status=0,  # Draft
            progress=0,
        )

        # 计算预估费用
        task.estimated_cost = await self.billing_service.calculate_task_cost(task)

        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # 创建任务日志
        await self._add_task_log(task.id, "INFO", "Task created")

        return task

    async def get_tasks(
        self,
        user_id: UUID,
        status: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Task], int]:
        """
        获取任务列表

        Args:
            user_id: 用户ID
            status: 任务状态过滤
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            tuple[List[Task], int]: (任务列表, 总数)
        """
        # 构建查询
        query = select(Task).where(Task.user_id == user_id)
        count_query = select(func.count(Task.id)).where(Task.user_id == user_id)

        # 状态过滤
        if status is not None:
            query = query.where(Task.status == status)
            count_query = count_query.where(Task.status == status)

        # 查询总数
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询任务列表
        result = await self.db.execute(
            query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
        )
        tasks = result.scalars().all()

        return list(tasks), total

    async def get_task_by_id(self, task_id: UUID, user_id: UUID) -> Task:
        """
        获取任务详情

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            Task: 任务对象

        Raises:
            HTTPException: 任务不存在或无权限
        """
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or you don't have permission",
            )

        return task

    async def update_task_status(
        self, task_id: UUID, user_id: UUID, new_status: int, error_message: Optional[str] = None
    ) -> Task:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            user_id: 用户ID
            new_status: 新状态
            error_message: 错误消息（可选）

        Returns:
            Task: 更新后的任务对象

        Raises:
            HTTPException: 任务不存在或无权限
        """
        task = await self.get_task_by_id(task_id, user_id)

        old_status = task.status
        task.status = new_status

        if error_message:
            task.error_message = error_message

        await self.db.commit()
        await self.db.refresh(task)

        # 添加日志
        await self._add_task_log(
            task_id,
            "INFO",
            f"Task status changed from {old_status} to {new_status}",
        )

        return task

    async def pause_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        暂停任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            Task: 更新后的任务对象

        Raises:
            HTTPException: 任务不存在、无权限或状态不允许暂停
        """
        task = await self.get_task_by_id(task_id, user_id)

        # 检查任务状态（只有排队中或渲染中的任务可以暂停）
        if task.status not in [2, 3]:  # Queued, Rendering
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task cannot be paused in current status",
            )

        task.status = 4  # Paused
        await self.db.commit()
        await self.db.refresh(task)

        # 添加日志
        await self._add_task_log(task_id, "INFO", "Task paused")

        return task

    async def resume_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        恢复任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            Task: 更新后的任务对象

        Raises:
            HTTPException: 任务不存在、无权限或状态不是暂停
        """
        task = await self.get_task_by_id(task_id, user_id)

        # 检查任务状态（只有暂停的任务可以恢复）
        if task.status != 4:  # Paused
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is not paused",
            )

        task.status = 2  # Queued
        await self.db.commit()
        await self.db.refresh(task)

        # 添加日志
        await self._add_task_log(task_id, "INFO", "Task resumed")

        return task

    async def cancel_task(self, task_id: UUID, user_id: UUID) -> Task:
        """
        取消任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            Task: 更新后的任务对象

        Raises:
            HTTPException: 任务不存在、无权限或状态不允许取消
        """
        task = await self.get_task_by_id(task_id, user_id)

        # 检查任务状态（已完成、失败、已取消的任务不能再次取消）
        if task.status in [5, 6, 7]:  # Completed, Failed, Cancelled
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task cannot be cancelled in current status",
            )

        task.status = 7  # Cancelled
        await self.db.commit()
        await self.db.refresh(task)

        # 添加日志
        await self._add_task_log(task_id, "WARNING", "Task cancelled by user")

        return task

    async def delete_task(self, task_id: UUID, user_id: UUID) -> None:
        """
        删除任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Raises:
            HTTPException: 任务不存在、无权限或状态不允许删除
        """
        task = await self.get_task_by_id(task_id, user_id)

        # 检查任务状态（正在渲染的任务不能删除）
        if task.status == 3:  # Rendering
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a task that is currently rendering",
            )

        await self.db.delete(task)
        await self.db.commit()

    async def get_task_logs(
        self, task_id: UUID, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[List[TaskLog], int]:
        """
        获取任务日志

        Args:
            task_id: 任务ID
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            tuple[List[TaskLog], int]: (日志列表, 总数)

        Raises:
            HTTPException: 任务不存在或无权限
        """
        # 验证任务权限
        await self.get_task_by_id(task_id, user_id)

        # 查询总数
        count_result = await self.db.execute(
            select(func.count(TaskLog.id)).where(TaskLog.task_id == task_id)
        )
        total = count_result.scalar() or 0

        # 查询日志
        result = await self.db.execute(
            select(TaskLog)
            .where(TaskLog.task_id == task_id)
            .order_by(TaskLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        logs = result.scalars().all()

        return list(logs), total

    async def _add_task_log(
        self, task_id: UUID, log_level: str, message: str
    ) -> TaskLog:
        """
        添加任务日志（内部方法）

        Args:
            task_id: 任务ID
            log_level: 日志级别
            message: 日志消息

        Returns:
            TaskLog: 日志对象
        """
        log = TaskLog(task_id=task_id, log_level=log_level, message=message)

        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        return log
