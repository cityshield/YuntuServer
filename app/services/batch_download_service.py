"""
批量下载服务 - 实现架构文档 §六.阶段5
"""
from typing import Optional
from uuid import UUID
import zipfile
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.upload_task import UploadTask, TaskStatus
from app.models.task_file import TaskFile, FileUploadStatus
from app.services.oss_service import OSSService
from app.services.upload_task_service import UploadTaskService


class BatchDownloadService:
    """批量下载服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.oss_service = OSSService()
        self.task_service = UploadTaskService(db)

    async def generate_download_links(
        self, task_id: UUID, user_id: UUID, expires_in: int = 3600
    ) -> dict:
        """
        生成批量下载链接

        为任务中的所有文件生成临时下载链接

        Args:
            task_id: 任务ID
            user_id: 用户ID
            expires_in: 过期时间（秒），默认1小时

        Returns:
            Dict: {
                download_url: str,  # 主下载链接（如果支持打包）
                expires_in: int,
                file_count: int,
                total_size: int,
                files: List[{file_id, file_name, download_url}]
            }
        """
        # 验证任务所有权和状态
        task = await self._get_completed_task(task_id, user_id)

        # 查询所有已完成的文件
        files_result = await self.db.execute(
            select(TaskFile).where(
                TaskFile.task_id == task_id,
                TaskFile.status.in_([FileUploadStatus.COMPLETED, FileUploadStatus.SKIPPED])
            )
        )
        files = files_result.scalars().all()

        if not files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No files found in this task"
            )

        # 为每个文件生成下载链接
        file_links = []
        total_size = 0

        for file in files:
            if file.oss_key:
                download_url = await self.oss_service.generate_presigned_url(
                    file.oss_key, expires_in
                )
                file_links.append({
                    "file_id": str(file.file_id),
                    "task_file_id": str(file.id),
                    "file_name": file.file_name,
                    "file_size": file.file_size,
                    "download_url": download_url,
                })
                total_size += file.file_size

        return {
            "download_url": None,  # 单独的打包下载链接在 create_archive 中生成
            "expires_in": expires_in,
            "file_count": len(file_links),
            "total_size": total_size,
            "files": file_links,
        }

    async def create_archive(
        self,
        task_id: UUID,
        user_id: UUID,
        archive_name: Optional[str] = None,
        format: str = "zip",
    ) -> dict:
        """
        创建打包任务（ZIP 格式）

        将任务中的所有文件打包成 ZIP 并返回下载链接

        根据架构文档 §六.阶段5

        Args:
            task_id: 任务ID
            user_id: 用户ID
            archive_name: 压缩包名称（不含扩展名）
            format: 打包格式，目前只支持 zip

        Returns:
            Dict: {
                archive_id: UUID,
                status: str,
                download_url: str,
                expires_at: str
            }
        """
        if format != "zip":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only ZIP format is supported"
            )

        # 验证任务
        task = await self._get_completed_task(task_id, user_id)

        # 查询所有已完成的文件
        files_result = await self.db.execute(
            select(TaskFile).where(
                TaskFile.task_id == task_id,
                TaskFile.status.in_([FileUploadStatus.COMPLETED, FileUploadStatus.SKIPPED])
            )
        )
        files = files_result.scalars().all()

        if not files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No files found in this task"
            )

        # 生成压缩包名称
        if not archive_name:
            archive_name = f"{task.task_name}_{task.id}"

        # 创建内存中的 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file in files:
                if file.oss_key:
                    # 从 OSS 下载文件内容
                    file_content = await self.oss_service.download_file(file.oss_key)

                    # 构建 ZIP 中的文件路径（保留虚拟路径结构）
                    zip_path = file.virtual_path.lstrip("/")

                    # 添加到 ZIP
                    zip_file.writestr(zip_path, file_content)

        # 上传 ZIP 到 OSS 临时区域
        zip_data = zip_buffer.getvalue()
        zip_oss_key = f"temp/archives/{task_id}/{archive_name}.zip"
        zip_url = await self.oss_service.upload_file(zip_oss_key, zip_data)

        # 生成临时下载链接（1小时有效）
        download_url = await self.oss_service.generate_presigned_url(
            zip_oss_key, expires_in=3600
        )

        # TODO: 可以在后台异步打包，这里简化为同步处理
        # 实际生产中应该创建 ArchiveTask 模型，记录打包任务状态

        from datetime import datetime, timedelta
        expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()

        return {
            "archive_id": task_id,  # 简化：使用 task_id 作为 archive_id
            "status": "completed",
            "download_url": download_url,
            "expires_at": expires_at,
            "file_count": len(files),
            "total_size": sum(f.file_size for f in files),
            "archive_size": len(zip_data),
        }

    async def _get_completed_task(self, task_id: UUID, user_id: UUID) -> UploadTask:
        """获取已完成的任务"""
        task = await self.task_service.get_task(task_id, user_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task is not completed yet"
            )

        return task
