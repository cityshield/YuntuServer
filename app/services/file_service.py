"""
文件管理服务
"""
import os
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.services.oss_service import oss_service
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger()


class FileService:
    """文件管理服务类"""

    def __init__(self):
        """初始化文件服务"""
        self.oss = oss_service

    def _generate_scene_path(self, task_id: UUID, filename: str) -> str:
        """
        生成场景文件的OSS路径

        Args:
            task_id: 任务ID
            filename: 文件名

        Returns:
            OSS对象键
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{settings.OSS_SCENE_FOLDER}/{timestamp}/{task_id}/{filename}"

    def _generate_result_path(self, task_id: UUID, filename: str) -> str:
        """
        生成渲染结果文件的OSS路径

        Args:
            task_id: 任务ID
            filename: 文件名

        Returns:
            OSS对象键
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{settings.OSS_RESULT_FOLDER}/{timestamp}/{task_id}/{filename}"

    async def upload_scene_file(
        self,
        task_id: UUID,
        filename: str,
        file_content: bytes,
        content_type: Optional[str] = None
    ) -> dict:
        """
        上传场景文件

        Args:
            task_id: 任务ID
            filename: 文件名
            file_content: 文件内容
            content_type: 文件MIME类型

        Returns:
            文件信息字典
        """
        try:
            # 生成OSS路径
            object_key = self._generate_scene_path(task_id, filename)

            # 上传文件
            file_url = self.oss.upload_file(
                file_content=file_content,
                object_key=object_key,
                content_type=content_type
            )

            logger.info(f"Scene file uploaded: {filename} for task {task_id}")

            return {
                "filename": filename,
                "object_key": object_key,
                "url": file_url,
                "size": len(file_content),
                "content_type": content_type,
                "uploaded_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to upload scene file: {str(e)}")
            raise

    async def upload_result_file(
        self,
        task_id: UUID,
        filename: str,
        file_content: bytes,
        content_type: Optional[str] = None
    ) -> dict:
        """
        上传渲染结果文件

        Args:
            task_id: 任务ID
            filename: 文件名
            file_content: 文件内容
            content_type: 文件MIME类型

        Returns:
            文件信息字典
        """
        try:
            # 生成OSS路径
            object_key = self._generate_result_path(task_id, filename)

            # 上传文件
            file_url = self.oss.upload_file(
                file_content=file_content,
                object_key=object_key,
                content_type=content_type
            )

            logger.info(f"Result file uploaded: {filename} for task {task_id}")

            return {
                "filename": filename,
                "object_key": object_key,
                "url": file_url,
                "size": len(file_content),
                "content_type": content_type,
                "uploaded_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to upload result file: {str(e)}")
            raise

    def get_download_url(
        self,
        object_key: str,
        filename: Optional[str] = None,
        expire_time: int = 3600
    ) -> str:
        """
        获取文件下载URL

        Args:
            object_key: OSS对象键
            filename: 下载文件名（可选）
            expire_time: URL过期时间（秒），默认1小时

        Returns:
            预签名下载URL
        """
        try:
            # 检查文件是否存在
            if not self.oss.file_exists(object_key):
                raise FileNotFoundError(f"File not found: {object_key}")

            # 生成下载URL
            download_url = self.oss.generate_download_url(
                object_key=object_key,
                expire_time=expire_time,
                filename=filename
            )

            logger.info(f"Download URL generated for: {object_key}")
            return download_url

        except Exception as e:
            logger.error(f"Failed to get download URL: {str(e)}")
            raise

    def get_upload_url(
        self,
        task_id: UUID,
        filename: str,
        content_type: Optional[str] = None,
        expire_time: int = 3600
    ) -> dict:
        """
        获取文件上传URL（用于客户端直接上传）

        Args:
            task_id: 任务ID
            filename: 文件名
            content_type: 文件MIME类型
            expire_time: URL过期时间（秒），默认1小时

        Returns:
            上传信息字典
        """
        try:
            # 生成OSS路径
            object_key = self._generate_scene_path(task_id, filename)

            # 生成上传URL
            upload_url = self.oss.generate_upload_url(
                object_key=object_key,
                expire_time=expire_time,
                content_type=content_type
            )

            logger.info(f"Upload URL generated for: {filename}")

            return {
                "upload_url": upload_url,
                "object_key": object_key,
                "filename": filename,
                "expires_in": expire_time
            }

        except Exception as e:
            logger.error(f"Failed to get upload URL: {str(e)}")
            raise

    async def delete_file(self, object_key: str) -> bool:
        """
        删除文件

        Args:
            object_key: OSS对象键

        Returns:
            是否删除成功
        """
        try:
            result = self.oss.delete_file(object_key)
            if result:
                logger.info(f"File deleted: {object_key}")
            return result

        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise

    def get_file_info(self, object_key: str) -> dict:
        """
        获取文件信息

        Args:
            object_key: OSS对象键

        Returns:
            文件信息字典
        """
        try:
            file_info = self.oss.get_file_info(object_key)
            logger.info(f"File info retrieved: {object_key}")
            return file_info

        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            raise


# 创建全局文件服务实例
file_service = FileService()
