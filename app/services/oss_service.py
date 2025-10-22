"""
阿里云OSS服务
"""
import oss2
from typing import Optional
from datetime import datetime, timedelta
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger()


class OSSService:
    """阿里云OSS服务类"""

    def __init__(self):
        """初始化OSS服务"""
        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET_NAME
        )
        # 打印关键信息，便于定位 bucket/endpoint 配置
        logger.info(
            f"OSS Service initialized - Bucket: {settings.OSS_BUCKET_NAME}, Endpoint: {settings.OSS_ENDPOINT}, BaseURL: {settings.OSS_BASE_URL}"
        )

    def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到OSS

        Args:
            file_content: 文件内容（字节）
            object_key: OSS对象键（文件路径）
            content_type: 文件MIME类型

        Returns:
            文件的访问URL
        """
        try:
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type

            # 上传文件
            result = self.bucket.put_object(
                object_key,
                file_content,
                headers=headers
            )

            if result.status == 200:
                file_url = f"{settings.OSS_BASE_URL}/{object_key}"
                logger.info(f"File uploaded successfully: {object_key}")
                return file_url
            else:
                raise Exception(f"Upload failed with status: {result.status}")

        except Exception as e:
            logger.error(f"Failed to upload file to OSS: {str(e)}")
            raise

    def generate_upload_url(
        self,
        object_key: str,
        expire_time: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """
        生成上传签名URL

        Args:
            object_key: OSS对象键（文件路径）
            expire_time: 签名过期时间（秒），默认1小时
            content_type: 文件MIME类型

        Returns:
            预签名上传URL
        """
        try:
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type

            # 生成签名URL
            url = self.bucket.sign_url(
                'PUT',
                object_key,
                expire_time,
                headers=headers
            )

            logger.info(f"Generated upload URL for: {object_key}")
            return url

        except Exception as e:
            logger.error(f"Failed to generate upload URL: {str(e)}")
            raise

    def generate_download_url(
        self,
        object_key: str,
        expire_time: int = 3600,
        filename: Optional[str] = None
    ) -> str:
        """
        生成下载URL

        Args:
            object_key: OSS对象键（文件路径）
            expire_time: 签名过期时间（秒），默认1小时
            filename: 下载时的文件名

        Returns:
            预签名下载URL
        """
        try:
            params = {}
            if filename:
                # 设置下载时的文件名
                params['response-content-disposition'] = f'attachment; filename="{filename}"'

            # 生成签名URL
            url = self.bucket.sign_url(
                'GET',
                object_key,
                expire_time,
                params=params
            )

            logger.info(f"Generated download URL for: {object_key}")
            return url

        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise

    def delete_file(self, object_key: str) -> bool:
        """
        删除文件

        Args:
            object_key: OSS对象键（文件路径）

        Returns:
            是否删除成功
        """
        try:
            result = self.bucket.delete_object(object_key)

            if result.status == 204:
                logger.info(f"File deleted successfully: {object_key}")
                return True
            else:
                logger.warning(f"Delete failed with status: {result.status}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete file from OSS: {str(e)}")
            raise

    def file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在

        Args:
            object_key: OSS对象键（文件路径）

        Returns:
            文件是否存在
        """
        try:
            return self.bucket.object_exists(object_key)
        except Exception as e:
            logger.error(f"Failed to check file existence: {str(e)}")
            return False

    def get_file_info(self, object_key: str) -> dict:
        """
        获取文件信息

        Args:
            object_key: OSS对象键（文件路径）

        Returns:
            文件元数据信息
        """
        try:
            meta = self.bucket.head_object(object_key)
            return {
                "size": meta.content_length,
                "content_type": meta.content_type,
                "last_modified": meta.last_modified,
                "etag": meta.etag
            }
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            raise


# 创建全局OSS服务实例
oss_service = OSSService()
