"""
文件上传服务 - 实现架构文档 §六.阶段2 和 §六.阶段3
"""
from typing import List, Optional, Dict, BinaryIO
from uuid import UUID
import hashlib
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile

from app.models.task_file import TaskFile, FileUploadStatus
from app.models.file import File, UploadSource
from app.models.folder import Folder
from app.models.upload_task import UploadTask
from app.services.oss_service import OSSService
from app.services.upload_task_service import UploadTaskService
from app.schemas.file_upload import (
    FileCheckItem,
    ExistingFileInfo,
    MultipartInitRequest,
)


class FileUploadService:
    """文件上传服务类"""

    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB 分片大小
    LARGE_FILE_THRESHOLD = 5 * 1024 * 1024  # 5MB 以上使用分片上传

    def __init__(self, db: AsyncSession):
        self.db = db
        self.oss_service = OSSService()
        self.task_service = UploadTaskService(db)

    async def check_files_exist(
        self, task_id: UUID, files: List[FileCheckItem], user_id: UUID
    ) -> Dict:
        """
        批量检查文件是否存在（秒传检测）

        根据架构文档 §六.阶段2

        Args:
            task_id: 任务ID
            files: 待检查的文件列表
            user_id: 用户ID

        Returns:
            Dict: {existing_files: [...], new_files_count: int, storage_saved: int}
        """
        # 验证任务所有权
        task = await self.task_service.get_task(task_id, user_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied"
            )

        # 提取所有 MD5
        md5_list = [f.md5 for f in files if f.md5]
        if not md5_list:
            return {
                "existing_files": [],
                "new_files_count": len(files),
                "storage_saved": 0,
            }

        # 批量查询已存在的文件
        result = await self.db.execute(
            select(File).where(File.md5.in_(md5_list))
        )
        existing_files_db = result.scalars().all()

        # 创建 MD5 到文件的映射
        md5_to_file = {f.md5: f for f in existing_files_db}

        # 处理已存在的文件
        existing_files_info = []
        storage_saved = 0

        for check_item in files:
            if check_item.md5 in md5_to_file:
                existing_file = md5_to_file[check_item.md5]

                # 更新 TaskFile 状态为 skipped
                task_file_result = await self.db.execute(
                    select(TaskFile).where(TaskFile.id == check_item.task_file_id)
                )
                task_file = task_file_result.scalar_one_or_none()

                if task_file:
                    task_file.status = FileUploadStatus.SKIPPED
                    task_file.is_duplicated = True
                    task_file.duplicated_from = existing_file.id
                    task_file.oss_key = existing_file.oss_key
                    task_file.oss_url = existing_file.oss_url

                    # 创建新的 File 记录（引用相同的 OSS 文件）
                    new_file = File(
                        name=task_file.file_name,
                        original_name=task_file.file_name,
                        size=task_file.file_size,
                        extension=self._get_file_extension(task_file.file_name),
                        mime_type=task_file.mime_type,
                        oss_key=existing_file.oss_key,
                        oss_url=existing_file.oss_url,
                        md5=check_item.md5,
                        drive_id=task.drive_id,
                        uploaded_by=user_id,
                        upload_source=UploadSource.CLIENT,
                    )
                    self.db.add(new_file)
                    await self.db.flush()

                    task_file.file_id = new_file.id
                    task_file.upload_progress = 100.0

                    existing_files_info.append(
                        ExistingFileInfo(
                            task_file_id=check_item.task_file_id,
                            md5=check_item.md5,
                            existing_file_id=existing_file.id,
                            oss_key=existing_file.oss_key,
                            oss_url=existing_file.oss_url,
                            file_size=check_item.file_size,
                        )
                    )

                    storage_saved += check_item.file_size

        await self.db.commit()

        # 更新任务进度
        await self._update_task_progress(task_id)

        return {
            "existing_files": existing_files_info,
            "new_files_count": len(files) - len(existing_files_info),
            "storage_saved": storage_saved,
        }

    async def upload_file(
        self,
        task_file_id: UUID,
        file: UploadFile,
        user_id: UUID,
    ) -> Dict:
        """
        上传单个文件（小文件直接上传）

        根据架构文档 §六.阶段3 - 小文件直接上传

        Args:
            task_file_id: 任务文件ID
            file: 上传的文件
            user_id: 用户ID

        Returns:
            Dict: 上传结果
        """
        start_time = time.time()

        # 查询 TaskFile
        task_file = await self._get_task_file(task_file_id, user_id)

        # 更新状态为上传中
        task_file.status = FileUploadStatus.UPLOADING
        await self.db.commit()

        try:
            # 读取文件内容
            content = await file.read()

            # 计算 MD5
            md5_hash = hashlib.md5(content).hexdigest()

            # 检查是否已存在（上传后去重）
            existing_file = await self._check_file_by_md5(md5_hash)

            if existing_file:
                # 秒传：不上传到 OSS，直接引用已存在的文件
                new_file = await self._create_file_reference(
                    task_file=task_file,
                    existing_file=existing_file,
                    user_id=user_id,
                    md5_hash=md5_hash,
                )

                task_file.status = FileUploadStatus.COMPLETED
                task_file.is_duplicated = True
                task_file.duplicated_from = existing_file.id
                task_file.file_id = new_file.id
                task_file.oss_key = existing_file.oss_key
                task_file.oss_url = existing_file.oss_url
                task_file.md5 = md5_hash
                task_file.upload_progress = 100.0

            else:
                # 上传到 OSS
                oss_key = self._generate_oss_key(task_file.file_name)
                oss_url = await self.oss_service.upload_file(oss_key, content)

                # 创建 File 记录
                new_file = await self._create_new_file(
                    task_file=task_file,
                    oss_key=oss_key,
                    oss_url=oss_url,
                    md5_hash=md5_hash,
                    user_id=user_id,
                )

                task_file.status = FileUploadStatus.COMPLETED
                task_file.file_id = new_file.id
                task_file.oss_key = oss_key
                task_file.oss_url = oss_url
                task_file.md5 = md5_hash
                task_file.upload_progress = 100.0

            await self.db.commit()

            # 更新任务进度（检查是否完成）
            await self._update_task_progress(task_file.task_id)
            await self.task_service.check_and_complete_task(task_file.task_id)

            upload_duration = time.time() - start_time

            return {
                "task_file_id": task_file_id,
                "file_id": new_file.id,
                "oss_key": task_file.oss_key,
                "oss_url": task_file.oss_url,
                "file_size": task_file.file_size,
                "md5": md5_hash,
                "is_duplicated": task_file.is_duplicated,
                "upload_duration": upload_duration,
            }

        except Exception as e:
            # 上传失败
            task_file.status = FileUploadStatus.FAILED
            task_file.error_message = str(e)
            task_file.retry_count += 1
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )

    async def init_multipart_upload(
        self, request: MultipartInitRequest, user_id: UUID
    ) -> Dict:
        """
        初始化分片上传

        根据架构文档 §六.阶段3 - 大文件分片上传

        Args:
            request: 初始化请求
            user_id: 用户ID

        Returns:
            Dict: {upload_id, chunk_size, total_chunks}
        """
        # 查询 TaskFile
        task_file = await self._get_task_file(request.task_file_id, user_id)

        # 生成 OSS key
        oss_key = self._generate_oss_key(request.file_name)

        # 初始化 OSS 分片上传
        upload_id = await self.oss_service.init_multipart_upload(oss_key)

        # 计算分片数
        total_chunks = (request.file_size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE

        # 更新 TaskFile
        task_file.status = FileUploadStatus.UPLOADING
        task_file.oss_key = oss_key
        task_file.chunk_info = {
            "upload_id": upload_id,
            "chunk_size": self.CHUNK_SIZE,
            "total_chunks": total_chunks,
            "uploaded_chunks": [],
            "chunk_etags": {},
        }
        await self.db.commit()

        return {
            "task_file_id": request.task_file_id,
            "upload_id": upload_id,
            "chunk_size": self.CHUNK_SIZE,
            "total_chunks": total_chunks,
        }

    async def upload_chunk(
        self,
        task_file_id: UUID,
        chunk_index: int,
        chunk_data: bytes,
        user_id: UUID,
    ) -> Dict:
        """
        上传单个分片

        Args:
            task_file_id: 任务文件ID
            chunk_index: 分片索引（从1开始）
            chunk_data: 分片数据
            user_id: 用户ID

        Returns:
            Dict: {chunk_index, chunk_etag, uploaded_chunks, total_chunks, progress_percentage}
        """
        # 查询 TaskFile
        task_file = await self._get_task_file(task_file_id, user_id)

        if not task_file.chunk_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart upload not initialized"
            )

        chunk_info = task_file.chunk_info
        upload_id = chunk_info["upload_id"]
        oss_key = task_file.oss_key

        # 上传分片到 OSS
        etag = await self.oss_service.upload_part(
            oss_key, upload_id, chunk_index, chunk_data
        )

        # 更新 chunk_info
        chunk_info["uploaded_chunks"].append(chunk_index)
        chunk_info["chunk_etags"][chunk_index] = etag
        task_file.chunk_info = chunk_info

        # 更新进度
        uploaded_count = len(chunk_info["uploaded_chunks"])
        total_chunks = chunk_info["total_chunks"]
        task_file.upload_progress = (uploaded_count / total_chunks) * 100

        await self.db.commit()

        return {
            "chunk_index": chunk_index,
            "chunk_etag": etag,
            "uploaded_chunks": uploaded_count,
            "total_chunks": total_chunks,
            "progress_percentage": task_file.upload_progress,
        }

    async def complete_multipart_upload(
        self,
        task_file_id: UUID,
        chunk_etags: Dict[int, str],
        user_id: UUID,
    ) -> Dict:
        """
        完成分片上传

        Args:
            task_file_id: 任务文件ID
            chunk_etags: 分片ETag映射
            user_id: 用户ID

        Returns:
            Dict: 上传结果
        """
        start_time = time.time()

        # 查询 TaskFile
        task_file = await self._get_task_file(task_file_id, user_id)

        if not task_file.chunk_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multipart upload not initialized"
            )

        chunk_info = task_file.chunk_info
        upload_id = chunk_info["upload_id"]
        oss_key = task_file.oss_key

        try:
            # 完成 OSS 分片上传
            oss_url = await self.oss_service.complete_multipart_upload(
                oss_key, upload_id, chunk_etags
            )

            # 计算文件 MD5（从 OSS 获取）
            md5_hash = await self.oss_service.get_file_md5(oss_key)

            # 检查去重
            existing_file = await self._check_file_by_md5(md5_hash)

            if existing_file:
                # 删除刚上传的 OSS 文件
                await self.oss_service.delete_file(oss_key)

                # 创建文件引用
                new_file = await self._create_file_reference(
                    task_file=task_file,
                    existing_file=existing_file,
                    user_id=user_id,
                    md5_hash=md5_hash,
                )

                task_file.is_duplicated = True
                task_file.duplicated_from = existing_file.id
                task_file.oss_key = existing_file.oss_key
                task_file.oss_url = existing_file.oss_url

            else:
                # 创建新文件记录
                new_file = await self._create_new_file(
                    task_file=task_file,
                    oss_key=oss_key,
                    oss_url=oss_url,
                    md5_hash=md5_hash,
                    user_id=user_id,
                )

            task_file.status = FileUploadStatus.COMPLETED
            task_file.file_id = new_file.id
            task_file.md5 = md5_hash
            task_file.upload_progress = 100.0
            task_file.chunk_info = None  # 清空分片信息

            await self.db.commit()

            # 更新任务进度
            await self._update_task_progress(task_file.task_id)
            await self.task_service.check_and_complete_task(task_file.task_id)

            upload_duration = time.time() - start_time

            return {
                "task_file_id": task_file_id,
                "file_id": new_file.id,
                "oss_key": task_file.oss_key,
                "oss_url": task_file.oss_url,
                "file_size": task_file.file_size,
                "md5": md5_hash,
                "is_duplicated": task_file.is_duplicated,
                "upload_duration": upload_duration,
            }

        except Exception as e:
            # 上传失败，中止分片上传
            await self.oss_service.abort_multipart_upload(oss_key, upload_id)
            task_file.status = FileUploadStatus.FAILED
            task_file.error_message = str(e)
            task_file.retry_count += 1
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Multipart upload failed: {str(e)}"
            )

    async def abort_multipart_upload(
        self, task_file_id: UUID, user_id: UUID, reason: Optional[str] = None
    ) -> None:
        """
        中止分片上传

        Args:
            task_file_id: 任务文件ID
            user_id: 用户ID
            reason: 中止原因
        """
        task_file = await self._get_task_file(task_file_id, user_id)

        if task_file.chunk_info:
            upload_id = task_file.chunk_info["upload_id"]
            oss_key = task_file.oss_key

            await self.oss_service.abort_multipart_upload(oss_key, upload_id)

            task_file.status = FileUploadStatus.FAILED
            task_file.error_message = reason or "Upload aborted by user"
            task_file.chunk_info = None

            await self.db.commit()

    async def retry_file(self, task_file_id: UUID, user_id: UUID) -> Dict:
        """
        重试失败的文件

        Args:
            task_file_id: 任务文件ID
            user_id: 用户ID

        Returns:
            Dict: {task_file_id, status, retry_count, message}
        """
        task_file = await self._get_task_file(task_file_id, user_id)

        if not task_file.can_retry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File cannot be retried (max retries reached or not failed)"
            )

        # 重置状态
        task_file.status = FileUploadStatus.PENDING
        task_file.error_message = None
        task_file.upload_progress = 0.0

        await self.db.commit()

        return {
            "task_file_id": task_file_id,
            "status": task_file.status.value,
            "retry_count": task_file.retry_count,
            "message": "File reset to pending, ready for retry",
        }

    # ==================== 辅助方法 ====================

    async def _get_task_file(self, task_file_id: UUID, user_id: UUID) -> TaskFile:
        """获取任务文件并验证权限"""
        result = await self.db.execute(
            select(TaskFile).where(TaskFile.id == task_file_id)
        )
        task_file = result.scalar_one_or_none()

        if not task_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task file not found"
            )

        # 验证任务所有权
        task = await self.task_service.get_task(task_file.task_id, user_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        return task_file

    async def _check_file_by_md5(self, md5: str) -> Optional[File]:
        """根据 MD5 查询文件是否已存在"""
        result = await self.db.execute(
            select(File).where(File.md5 == md5).limit(1)
        )
        return result.scalar_one_or_none()

    async def _create_file_reference(
        self,
        task_file: TaskFile,
        existing_file: File,
        user_id: UUID,
        md5_hash: str,
    ) -> File:
        """创建文件引用（秒传）"""
        # 查询 folder_id
        folder_id = await self._get_folder_id(
            task_file.task_id, task_file.target_folder_path
        )

        new_file = File(
            name=task_file.file_name,
            original_name=task_file.file_name,
            size=task_file.file_size,
            extension=self._get_file_extension(task_file.file_name),
            mime_type=task_file.mime_type,
            oss_key=existing_file.oss_key,
            oss_url=existing_file.oss_url,
            md5=md5_hash,
            drive_id=existing_file.drive_id,
            folder_id=folder_id,
            uploaded_by=user_id,
            upload_source=UploadSource.CLIENT,
        )
        self.db.add(new_file)
        await self.db.flush()
        return new_file

    async def _create_new_file(
        self,
        task_file: TaskFile,
        oss_key: str,
        oss_url: str,
        md5_hash: str,
        user_id: UUID,
    ) -> File:
        """创建新文件记录"""
        # 获取任务信息
        task_result = await self.db.execute(
            select(UploadTask).where(UploadTask.id == task_file.task_id)
        )
        task = task_result.scalar_one()

        # 查询 folder_id
        folder_id = await self._get_folder_id(
            task_file.task_id, task_file.target_folder_path
        )

        new_file = File(
            name=task_file.file_name,
            original_name=task_file.file_name,
            size=task_file.file_size,
            extension=self._get_file_extension(task_file.file_name),
            mime_type=task_file.mime_type,
            oss_key=oss_key,
            oss_url=oss_url,
            md5=md5_hash,
            drive_id=task.drive_id,
            folder_id=folder_id,
            uploaded_by=user_id,
            upload_source=UploadSource.CLIENT,
        )
        self.db.add(new_file)
        await self.db.flush()
        return new_file

    async def _get_folder_id(self, task_id: UUID, folder_path: str) -> Optional[UUID]:
        """获取文件夹ID"""
        if not folder_path or folder_path == "/":
            return None

        task_result = await self.db.execute(
            select(UploadTask).where(UploadTask.id == task_id)
        )
        task = task_result.scalar_one()

        result = await self.db.execute(
            select(Folder).where(
                Folder.drive_id == task.drive_id,
                Folder.path == folder_path
            )
        )
        folder = result.scalar_one_or_none()
        return folder.id if folder else None

    async def _update_task_progress(self, task_id: UUID) -> None:
        """更新任务进度"""
        # 查询所有文件的状态
        files_result = await self.db.execute(
            select(TaskFile).where(TaskFile.task_id == task_id)
        )
        files = files_result.scalars().all()

        # 计算已完成的文件数和大小
        uploaded_files = sum(
            1 for f in files
            if f.status in [FileUploadStatus.COMPLETED, FileUploadStatus.SKIPPED]
        )
        uploaded_size = sum(
            f.file_size for f in files
            if f.status in [FileUploadStatus.COMPLETED, FileUploadStatus.SKIPPED]
        )

        # 更新任务
        task_result = await self.db.execute(
            select(UploadTask).where(UploadTask.id == task_id)
        )
        task = task_result.scalar_one()

        task.uploaded_files = uploaded_files
        task.uploaded_size = uploaded_size

        # 如果有文件在上传中，更新任务状态
        if any(f.status == FileUploadStatus.UPLOADING for f in files):
            task.status = TaskStatus.UPLOADING

        await self.db.commit()

    def _generate_oss_key(self, filename: str) -> str:
        """生成 OSS 对象键"""
        import uuid
        from datetime import datetime

        date_path = datetime.now().strftime("%Y/%m/%d")
        unique_id = str(uuid.uuid4())
        extension = self._get_file_extension(filename)
        return f"uploads/{date_path}/{unique_id}{extension}"

    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名"""
        import os
        return os.path.splitext(filename)[1]
