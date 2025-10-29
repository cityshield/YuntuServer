"""
智能 OSS 上传器
优化大文件上传性能，动态调整分片大小和并发数
"""
import oss2
import time
from typing import Optional, Callable
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger()


class SmartOSSUploader:
    """智能 OSS 上传器"""

    # 分片大小常量
    MIN_PART_SIZE = 1 * 1024 * 1024  # 1MB
    SMALL_PART_SIZE = 10 * 1024 * 1024  # 10MB
    MEDIUM_PART_SIZE = 20 * 1024 * 1024  # 20MB
    LARGE_PART_SIZE = 50 * 1024 * 1024  # 50MB

    # 文件大小阈值
    SMALL_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB
    MEDIUM_FILE_THRESHOLD = 1 * 1024 * 1024 * 1024  # 1GB

    # 并发线程数范围
    MIN_THREADS = 4
    MAX_THREADS = 20
    DEFAULT_THREADS = 8

    def __init__(self):
        """初始化上传器"""
        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET_NAME
        )
        logger.info(f"Smart OSS Uploader initialized with endpoint: {settings.OSS_ENDPOINT}")

    def calculate_optimal_part_size(self, file_size: int) -> int:
        """
        根据文件大小计算最优分片大小

        Args:
            file_size: 文件大小（字节）

        Returns:
            最优分片大小（字节）
        """
        if file_size < self.SMALL_FILE_THRESHOLD:
            # <100MB: 单片上传或小分片
            if file_size < 10 * 1024 * 1024:  # <10MB
                return file_size  # 单片上传
            else:
                return self.SMALL_PART_SIZE  # 10MB 分片

        elif file_size < self.MEDIUM_FILE_THRESHOLD:
            # 100MB - 1GB: 中等分片
            return self.MEDIUM_PART_SIZE  # 20MB 分片

        else:
            # >1GB: 大分片
            return self.LARGE_PART_SIZE  # 50MB 分片

    def calculate_optimal_threads(self, file_size: int, bandwidth_mbps: Optional[float] = None) -> int:
        """
        根据文件大小和带宽计算最优并发线程数

        Args:
            file_size: 文件大小（字节）
            bandwidth_mbps: 带宽（Mbps），如果为 None 则使用默认策略

        Returns:
            最优并发线程数
        """
        # 如果有带宽信息，根据带宽计算
        if bandwidth_mbps:
            # 每 10Mbps 分配 1 个线程
            threads = max(self.MIN_THREADS, min(self.MAX_THREADS, int(bandwidth_mbps / 10)))
            logger.debug(f"Calculated threads based on bandwidth {bandwidth_mbps}Mbps: {threads}")
            return threads

        # 否则根据文件大小计算
        if file_size < self.SMALL_FILE_THRESHOLD:
            threads = self.MIN_THREADS  # 小文件用最少线程
        elif file_size < self.MEDIUM_FILE_THRESHOLD:
            threads = self.DEFAULT_THREADS  # 中等文件用默认线程数
        else:
            threads = self.MAX_THREADS  # 大文件用最多线程

        logger.debug(f"Calculated threads based on file size {file_size} bytes: {threads}")
        return threads

    def measure_upload_bandwidth(self, test_size: int = 1 * 1024 * 1024) -> float:
        """
        测量上传带宽

        Args:
            test_size: 测试数据大小（字节），默认 1MB

        Returns:
            上传带宽（Mbps）
        """
        try:
            # 生成测试数据
            test_data = b'0' * test_size
            test_key = f"_bandwidth_test_{int(time.time())}.tmp"

            # 测速
            start_time = time.time()
            self.bucket.put_object(test_key, test_data)
            elapsed_time = time.time() - start_time

            # 计算带宽（Mbps）
            bandwidth_mbps = (test_size * 8 / 1024 / 1024) / elapsed_time

            # 清理测试文件
            try:
                self.bucket.delete_object(test_key)
            except:
                pass

            logger.info(f"Measured upload bandwidth: {bandwidth_mbps:.2f} Mbps")
            return bandwidth_mbps

        except Exception as e:
            logger.warning(f"Failed to measure bandwidth: {str(e)}, using default thread count")
            return None

    def upload_large_file(
        self,
        file_path: str,
        object_key: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        auto_optimize: bool = True
    ) -> str:
        """
        智能上传大文件（支持分片、断点续传、动态优化）

        Args:
            file_path: 本地文件路径
            object_key: OSS 对象键
            progress_callback: 进度回调函数 callback(uploaded_bytes, total_bytes)
            auto_optimize: 是否自动优化上传参数

        Returns:
            文件访问 URL
        """
        import os

        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            logger.info(f"Starting smart upload: {object_key} ({file_size} bytes)")

            # 计算最优参数
            if auto_optimize:
                # 测速（仅对大文件）
                bandwidth = None
                if file_size > 100 * 1024 * 1024:  # >100MB 才测速
                    bandwidth = self.measure_upload_bandwidth()

                part_size = self.calculate_optimal_part_size(file_size)
                thread_num = self.calculate_optimal_threads(file_size, bandwidth)
            else:
                part_size = self.MEDIUM_PART_SIZE
                thread_num = self.DEFAULT_THREADS

            logger.info(f"Upload parameters: part_size={part_size}, threads={thread_num}")

            # 小文件直接上传
            if file_size < 10 * 1024 * 1024:  # <10MB
                logger.info("Using simple upload for small file")
                with open(file_path, 'rb') as f:
                    result = self.bucket.put_object(object_key, f)

                if result.status == 200:
                    file_url = f"{settings.OSS_BASE_URL}/{object_key}"
                    logger.info(f"File uploaded successfully: {object_key}")
                    if progress_callback:
                        progress_callback(file_size, file_size)
                    return file_url
                else:
                    raise Exception(f"Upload failed with status: {result.status}")

            # 大文件分片上传
            else:
                logger.info("Using resumable upload for large file")

                # 包装进度回调
                def percentage_callback(consumed_bytes, total_bytes):
                    if consumed_bytes:
                        percentage = 100 * consumed_bytes / total_bytes
                        logger.debug(f"Upload progress: {percentage:.1f}% ({consumed_bytes}/{total_bytes} bytes)")
                        if progress_callback:
                            progress_callback(consumed_bytes, total_bytes)

                # 分片上传
                oss2.resumable_upload(
                    self.bucket,
                    object_key,
                    file_path,
                    multipart_threshold=10 * 1024 * 1024,  # 10MB 以上启用分片
                    part_size=part_size,
                    num_threads=thread_num,
                    progress_callback=percentage_callback
                )

                file_url = f"{settings.OSS_BASE_URL}/{object_key}"
                logger.info(f"Large file uploaded successfully: {object_key}")
                return file_url

        except Exception as e:
            logger.error(f"Failed to upload file: {str(e)}")
            raise

    def upload_file_from_bytes(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        从字节数据上传文件

        Args:
            file_content: 文件内容（字节）
            object_key: OSS 对象键
            content_type: 文件 MIME 类型

        Returns:
            文件访问 URL
        """
        try:
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type

            result = self.bucket.put_object(
                object_key,
                file_content,
                headers=headers
            )

            if result.status == 200:
                file_url = f"{settings.OSS_BASE_URL}/{object_key}"
                logger.info(f"File uploaded successfully from bytes: {object_key}")
                return file_url
            else:
                raise Exception(f"Upload failed with status: {result.status}")

        except Exception as e:
            logger.error(f"Failed to upload file from bytes: {str(e)}")
            raise

    def generate_upload_url(
        self,
        object_key: str,
        expire_time: int = 3600,
        content_type: Optional[str] = None
    ) -> str:
        """
        生成上传签名 URL

        Args:
            object_key: OSS 对象键
            expire_time: 签名过期时间（秒），默认 1 小时
            content_type: 文件 MIME 类型

        Returns:
            预签名上传 URL
        """
        try:
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type

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


# 创建全局智能上传器实例
smart_oss_uploader = SmartOSSUploader()
