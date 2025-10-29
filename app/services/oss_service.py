"""
阿里云OSS服务
"""
import oss2
from typing import Optional, Callable
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

    def generate_upload_url_with_callback(
        self,
        object_key: str,
        callback_url: str,
        callback_params: dict,
        expire_time: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """
        生成带回调参数的上传签名URL

        Args:
            object_key: OSS对象键（文件路径）
            callback_url: 回调URL（完整URL，如 https://api.example.com/oss-callback/upload-complete）
            callback_params: 回调参数字典
            expire_time: 签名过期时间（秒），默认1小时
            content_type: 文件MIME类型

        Returns:
            预签名上传URL（带回调参数）
        """
        try:
            import json
            import base64

            # 1. 构建回调参数
            callback_dict = {
                "callbackUrl": callback_url,
                "callbackBody": self._build_callback_body(callback_params),
                "callbackBodyType": "application/x-www-form-urlencoded"
            }

            # 2. Base64 编码回调参数
            callback_base64 = base64.b64encode(
                json.dumps(callback_dict).encode('utf-8')
            ).decode('utf-8')

            # 3. 构建自定义变量
            callback_var_dict = self._build_callback_var(callback_params)
            callback_var_base64 = base64.b64encode(
                json.dumps(callback_var_dict).encode('utf-8')
            ).decode('utf-8')

            # 4. 设置请求头
            headers = {
                "x-oss-callback": callback_base64,
                "x-oss-callback-var": callback_var_base64
            }

            if content_type:
                headers['Content-Type'] = content_type

            # 5. 生成签名URL
            url = self.bucket.sign_url(
                'PUT',
                object_key,
                expire_time,
                headers=headers
            )

            logger.info(f"Generated upload URL with callback for: {object_key}")
            logger.debug(f"Callback URL: {callback_url}")
            logger.debug(f"Callback params: {callback_params}")

            return url

        except Exception as e:
            logger.error(f"Failed to generate upload URL with callback: {str(e)}")
            raise

    def _build_callback_body(self, params: dict) -> str:
        """
        构建回调请求体（URL编码格式）

        OSS 回调时会将这些参数作为请求体发送到回调URL

        Args:
            params: 回调参数

        Returns:
            URL编码的回调体字符串
        """
        # OSS 系统变量
        callback_fields = [
            "bucket=${bucket}",
            "object=${object}",
            "etag=${etag}",
            "size=${size}",
            "mimeType=${mimeType}",
            "imageInfo.height=${imageInfo.height}",
            "imageInfo.width=${imageInfo.width}",
            "imageInfo.format=${imageInfo.format}"
        ]

        # 自定义变量
        for key in params.keys():
            callback_fields.append(f"{key}=${{{key}}}")

        return "&".join(callback_fields)

    def _build_callback_var(self, params: dict) -> dict:
        """
        构建回调自定义变量

        Args:
            params: 自定义参数

        Returns:
            自定义变量字典（键以 x: 开头）
        """
        callback_var = {}
        for key, value in params.items():
            # OSS 自定义变量必须以 x: 开头
            callback_var[f"x:{key}"] = str(value)

        return callback_var

    def upload_large_file_optimized(
        self,
        file_path: str,
        object_key: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        auto_optimize: bool = True
    ) -> str:
        """
        使用智能上传器上传大文件（优化版本）

        Args:
            file_path: 本地文件路径
            object_key: OSS 对象键
            progress_callback: 进度回调函数 callback(uploaded_bytes, total_bytes)
            auto_optimize: 是否自动优化上传参数（默认开启）

        Returns:
            文件访问 URL
        """
        try:
            from app.utils.oss_smart_uploader import smart_oss_uploader

            logger.info(f"Using smart uploader for: {object_key}")
            return smart_oss_uploader.upload_large_file(
                file_path=file_path,
                object_key=object_key,
                progress_callback=progress_callback,
                auto_optimize=auto_optimize
            )
        except Exception as e:
            logger.error(f"Smart upload failed, falling back to normal upload: {str(e)}")
            # 如果智能上传失败，降级到普通上传
            with open(file_path, 'rb') as f:
                result = self.bucket.put_object(object_key, f)

            if result.status == 200:
                return f"{settings.OSS_BASE_URL}/{object_key}"
            else:
                raise Exception(f"Upload failed with status: {result.status}")


# 创建全局OSS服务实例
oss_service = OSSService()
