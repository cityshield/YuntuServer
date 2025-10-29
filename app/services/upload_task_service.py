"""
上传任务服务
"""
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException, status
from datetime import datetime

from app.models.upload_task import UploadTask, TaskStatus
from app.models.task_file import TaskFile, FileUploadStatus
from app.models.folder import Folder
from app.models.drive import Drive
from app.models.file import File, UploadSource
from app.schemas.upload_task import (
    UploadManifest,
    UploadTaskUpdate,
    StorageManifest,
    StorageManifestSummary,
    StorageManifestFile,
)


class UploadTaskService:
    """上传任务服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self, upload_manifest: UploadManifest, user_id: UUID
    ) -> UploadTask:
        """
        创建上传任务

        根据架构文档 §六.阶段1
        1. 创建 UploadTask (status=pending)
        2. 批量创建 TaskFile (status=pending)
        3. 解析 target_folder_path
        4. 自动创建不存在的 Folder

        Args:
            upload_manifest: 上传描述文件
            user_id: 用户ID

        Returns:
            UploadTask: 创建的任务对象
        """
        # 验证 drive 存在且用户有权限
        drive_result = await self.db.execute(
            select(Drive).where(
                Drive.id == upload_manifest.drive_id,
                or_(Drive.user_id == user_id, Drive.is_team_drive == True)  # 简化权限检查
            )
        )
        drive = drive_result.scalar_one_or_none()
        if not drive:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Drive not found or access denied"
            )

        # 创建上传任务
        # 使用 mode='json' 确保所有 UUID 和其他类型都被正确序列化为 JSON 兼容的格式
        manifest_dict = upload_manifest.model_dump(mode='json')

        task = UploadTask(
            user_id=user_id,
            drive_id=upload_manifest.drive_id,
            task_name=upload_manifest.task_name,
            priority=upload_manifest.priority,
            total_files=upload_manifest.total_files,
            total_size=upload_manifest.total_size,
            upload_manifest=manifest_dict,
            status=TaskStatus.PENDING,
        )
        self.db.add(task)
        await self.db.flush()  # 获取 task.id

        # 批量创建 TaskFile 记录
        for file_info in upload_manifest.files:
            # 确保目标文件夹存在（自动创建）
            folder = await self._ensure_folder_exists(
                drive_id=upload_manifest.drive_id,
                folder_path=file_info.target_folder_path,
                user_id=user_id
            )

            task_file = TaskFile(
                task_id=task.id,
                local_path=file_info.local_path,
                target_folder_path=file_info.target_folder_path,
                file_name=file_info.file_name,
                file_size=file_info.file_size,
                md5=file_info.md5,
                mime_type=file_info.mime_type,
                status=FileUploadStatus.PENDING,
            )
            self.db.add(task_file)

        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def _ensure_folder_exists(
        self, drive_id: UUID, folder_path: str, user_id: UUID
    ) -> Optional[Folder]:
        """
        确保文件夹存在，不存在则自动创建（递归创建父文件夹）

        Args:
            drive_id: 盘符ID
            folder_path: 文件夹路径（如 "/Documents/Photos"）
            user_id: 用户ID

        Returns:
            Folder: 文件夹对象（根目录返回None）
        """
        if not folder_path or folder_path == "/":
            return None

        # 查询是否已存在
        result = await self.db.execute(
            select(Folder).where(
                Folder.drive_id == drive_id,
                Folder.path == folder_path
            )
        )
        existing_folder = result.scalar_one_or_none()
        if existing_folder:
            return existing_folder

        # 解析路径
        path_parts = folder_path.strip("/").split("/")
        current_path = ""
        parent_folder = None

        # 递归创建所有层级的文件夹
        for i, part in enumerate(path_parts):
            current_path += f"/{part}"

            # 检查当前层级是否存在
            result = await self.db.execute(
                select(Folder).where(
                    Folder.drive_id == drive_id,
                    Folder.path == current_path
                )
            )
            folder = result.scalar_one_or_none()

            if not folder:
                # 创建新文件夹
                folder = Folder(
                    drive_id=drive_id,
                    name=part,
                    path=current_path,
                    level=i,
                    parent_id=parent_folder.id if parent_folder else None,
                    created_by=user_id,
                )
                self.db.add(folder)
                await self.db.flush()

            parent_folder = folder

        return parent_folder

    async def get_task(self, task_id: UUID, user_id: UUID) -> Optional[UploadTask]:
        """
        获取任务详情

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            Optional[UploadTask]: 任务对象
        """
        result = await self.db.execute(
            select(UploadTask).where(
                UploadTask.id == task_id,
                UploadTask.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        user_id: UUID,
        status_filter: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[UploadTask], int]:
        """
        获取任务列表

        Args:
            user_id: 用户ID
            status_filter: 状态筛选
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            Tuple[List[UploadTask], int]: (任务列表, 总数)
        """
        query = select(UploadTask).where(UploadTask.user_id == user_id)

        if status_filter:
            query = query.where(UploadTask.status == status_filter)

        # 查询总数
        count_result = await self.db.execute(
            select(func.count(UploadTask.id)).where(UploadTask.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # 查询任务列表
        query = query.order_by(UploadTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total

    async def get_task_files(
        self, task_id: UUID, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List[TaskFile], int]:
        """
        获取任务文件列表

        Args:
            task_id: 任务ID
            user_id: 用户ID
            skip: 跳过记录数
            limit: 返回记录数

        Returns:
            Tuple[List[TaskFile], int]: (文件列表, 总数)
        """
        # 验证任务所有权
        task = await self.get_task(task_id, user_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        # 查询总数
        count_result = await self.db.execute(
            select(func.count(TaskFile.id)).where(TaskFile.task_id == task_id)
        )
        total = count_result.scalar() or 0

        # 查询文件列表
        result = await self.db.execute(
            select(TaskFile)
            .where(TaskFile.task_id == task_id)
            .order_by(TaskFile.created_at)
            .offset(skip)
            .limit(limit)
        )
        files = result.scalars().all()

        return list(files), total

    async def update_task_status(
        self, task_id: UUID, user_id: UUID, new_status: TaskStatus
    ) -> UploadTask:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            user_id: 用户ID
            new_status: 新状态

        Returns:
            UploadTask: 更新后的任务
        """
        task = await self.get_task(task_id, user_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        task.status = new_status
        if new_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def cancel_task(self, task_id: UUID, user_id: UUID) -> UploadTask:
        """
        取消任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            UploadTask: 取消后的任务
        """
        return await self.update_task_status(task_id, user_id, TaskStatus.CANCELLED)

    async def check_and_complete_task(self, task_id: UUID) -> Optional[UploadTask]:
        """
        检查任务是否完成，如果所有文件都已完成则自动完成任务

        根据架构文档 §六.阶段4

        Args:
            task_id: 任务ID

        Returns:
            Optional[UploadTask]: 如果任务完成则返回任务对象
        """
        # 查询任务
        task_result = await self.db.execute(
            select(UploadTask).where(UploadTask.id == task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            return None

        # 查询所有文件状态
        files_result = await self.db.execute(
            select(TaskFile).where(TaskFile.task_id == task_id)
        )
        files = files_result.scalars().all()

        # 检查是否所有文件都已完成（completed 或 skipped）
        all_completed = all(
            f.status in [FileUploadStatus.COMPLETED, FileUploadStatus.SKIPPED]
            for f in files
        )

        if all_completed and task.status != TaskStatus.COMPLETED:
            # 生成 storage_manifest
            storage_manifest = await self.generate_storage_manifest(task_id)

            # 更新任务状态
            task.status = TaskStatus.COMPLETED
            task.storage_manifest = storage_manifest.model_dump(mode='json')
            task.completed_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(task)

        return task if all_completed else None

    async def generate_storage_manifest(self, task_id: UUID) -> StorageManifest:
        """
        生成存储描述文件

        根据架构文档 §4.2

        Args:
            task_id: 任务ID

        Returns:
            StorageManifest: 存储描述文件
        """
        # 查询任务和文件
        task_result = await self.db.execute(
            select(UploadTask).where(UploadTask.id == task_id)
        )
        task = task_result.scalar_one()

        files_result = await self.db.execute(
            select(TaskFile).where(TaskFile.task_id == task_id)
        )
        files = files_result.scalars().all()

        # 查询 drive 信息
        drive_result = await self.db.execute(
            select(Drive).where(Drive.id == task.drive_id)
        )
        drive = drive_result.scalar_one()

        # 统计信息
        uploaded_files = sum(1 for f in files if f.status == FileUploadStatus.COMPLETED)
        skipped_files = sum(1 for f in files if f.status == FileUploadStatus.SKIPPED)
        failed_files = sum(1 for f in files if f.status == FileUploadStatus.FAILED)
        storage_saved = sum(f.file_size for f in files if f.is_duplicated)

        # 生成文件列表
        manifest_files = []
        local_to_oss = {}
        local_to_virtual = {}
        oss_to_file_id = {}

        for f in files:
            if f.file_id and f.oss_key:
                manifest_file = StorageManifestFile(
                    file_id=f.file_id,
                    task_file_id=f.id,
                    file_name=f.file_name,
                    local_path=f.local_path,
                    virtual_path=f.virtual_path,
                    folder_id=None,  # TODO: 需要查询 folder_id
                    oss_key=f.oss_key,
                    oss_url=f.oss_url,
                    file_size=f.file_size,
                    md5=f.md5 or "",
                    upload_status=f.status.value,
                    is_duplicated=f.is_duplicated,
                    upload_duration=0.0,  # TODO: 计算上传耗时
                )
                manifest_files.append(manifest_file)

                # 生成映射
                local_to_oss[f.local_path] = f.oss_key
                local_to_virtual[f.local_path] = f.virtual_path
                oss_to_file_id[f.oss_key] = str(f.file_id)

        # 生成摘要
        summary = StorageManifestSummary(
            total_files=task.total_files,
            uploaded_files=uploaded_files,
            failed_files=failed_files,
            skipped_files=skipped_files,
            total_size=task.total_size,
            storage_saved=storage_saved,
        )

        # 生成完整的 storage_manifest
        manifest = StorageManifest(
            task_id=task.id,
            task_name=task.task_name,
            user_id=task.user_id,
            drive_id=task.drive_id,
            drive_name=drive.name,
            status=task.status,
            summary=summary,
            completed_at=task.completed_at,
            files=manifest_files,
            mappings={
                "local_to_oss": local_to_oss,
                "local_to_virtual": local_to_virtual,
                "oss_to_file_id": oss_to_file_id,
            },
        )

        return manifest

    async def mark_file_completed(
        self,
        task_id: UUID,
        file_id: UUID,
        user_id: UUID,
        oss_key: str,
        oss_url: str,
        md5: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> TaskFile:
        """
        标记文件上传完成

        根据架构文档 §六.阶段3
        1. 更新 TaskFile 状态为 COMPLETED
        2. 创建 File 数据库记录
        3. 更新 UploadTask 进度计数器
        4. 检查并自动完成任务

        Args:
            task_id: 任务ID
            file_id: 任务文件ID（TaskFile.id）
            user_id: 用户ID
            oss_key: OSS对象键
            oss_url: OSS访问URL
            md5: MD5哈希值
            file_size: 实际文件大小

        Returns:
            TaskFile: 更新后的任务文件对象

        Raises:
            HTTPException: 任务不存在或无权限
        """
        # 验证任务所有权
        task = await self.get_task(task_id, user_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        # 查询 TaskFile
        task_file_result = await self.db.execute(
            select(TaskFile).where(
                TaskFile.id == file_id,
                TaskFile.task_id == task_id
            )
        )
        task_file = task_file_result.scalar_one_or_none()
        if not task_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task file not found"
            )

        # 更新 TaskFile
        task_file.status = FileUploadStatus.COMPLETED
        task_file.oss_key = oss_key
        task_file.oss_url = oss_url
        task_file.upload_progress = 100.0
        task_file.completed_at = datetime.utcnow()

        if md5:
            task_file.md5 = md5
        if file_size:
            task_file.file_size = file_size

        # 创建 File 数据库记录
        # 根据 target_folder_path 查找 folder_id
        folder_id = None
        if task_file.target_folder_path and task_file.target_folder_path != "/":
            folder_result = await self.db.execute(
                select(Folder).where(
                    Folder.drive_id == task.drive_id,
                    Folder.path == task_file.target_folder_path
                )
            )
            folder = folder_result.scalar_one_or_none()
            if folder:
                folder_id = folder.id

        # 提取文件扩展名
        import os
        extension = os.path.splitext(task_file.file_name)[1]  # 如 ".ma", ".zip"

        # 创建 File 记录
        file_record = File(
            drive_id=task.drive_id,
            folder_id=folder_id,
            name=task_file.file_name,
            original_name=task_file.file_name,  # 原始文件名
            extension=extension,                 # 文件扩展名
            oss_key=oss_key,
            oss_url=oss_url,
            size=task_file.file_size,
            md5=task_file.md5,
            mime_type=task_file.mime_type,
            uploaded_by=user_id,
            upload_source=UploadSource.CLIENT,  # 客户端上传
        )
        self.db.add(file_record)
        await self.db.flush()

        # 更新 TaskFile 的 file_id
        task_file.file_id = file_record.id

        # 更新 UploadTask 进度
        task.uploaded_files = task.uploaded_files + 1
        task.uploaded_size = task.uploaded_size + task_file.file_size

        # 如果任务还在 PENDING 状态，改为 UPLOADING
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.UPLOADING

        await self.db.commit()
        await self.db.refresh(task_file)

        # 检查是否所有文件都已完成，自动完成任务
        await self.check_and_complete_task(task_id)

        return task_file
