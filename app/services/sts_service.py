"""
阿里云 STS 临时授权服务
"""
from typing import Dict
from datetime import datetime, timedelta
from alibabacloud_sts20150401.client import Client as StsClient
from alibabacloud_sts20150401.models import AssumeRoleRequest
from alibabacloud_tea_openapi.models import Config as StsConfig
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger()


class STSService:
    """阿里云 STS 临时授权服务类"""

    def __init__(self):
        """初始化 STS 服务"""
        # 配置 STS 客户端
        config = StsConfig(
            access_key_id=settings.OSS_ACCESS_KEY_ID,
            access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
            # STS endpoint (中国大陆)
            endpoint=getattr(settings, 'STS_ENDPOINT', 'sts.cn-beijing.aliyuncs.com')
        )

        self.client = StsClient(config)
        logger.info("STS Service initialized")

    def get_upload_credentials(
        self,
        user_id: int,
        task_id: str,
        duration_seconds: int = 3600
    ) -> Dict[str, str]:
        """
        获取上传文件的 STS 临时凭证

        Args:
            user_id: 用户 ID
            task_id: 任务 ID
            duration_seconds: 凭证有效期（秒），默认 1 小时

        Returns:
            STS 临时凭证字典：
            {
                "accessKeyId": "...",
                "accessKeySecret": "...",
                "securityToken": "...",
                "expiration": "2025-01-01T12:00:00Z"
            }
        """
        try:
            # RAM 角色 ARN（需要在阿里云 RAM 控制台创建）
            role_arn = getattr(
                settings,
                'OSS_ROLE_ARN',
                f'acs:ram::{settings.OSS_ACCESS_KEY_ID}:role/ossuploadrole'
            )

            # 创建 AssumeRole 请求
            request = AssumeRoleRequest(
                role_arn=role_arn,
                role_session_name=f"user_{user_id}_task_{task_id}",
                duration_seconds=duration_seconds,
                # 可选：添加更精细的权限策略
                # policy=self._generate_upload_policy(task_id)
            )

            # 调用 AssumeRole API
            response = self.client.assume_role(request)

            if not response or not response.body or not response.body.credentials:
                raise Exception("Failed to get STS credentials: empty response")

            credentials = response.body.credentials

            logger.info(f"Generated STS credentials for user {user_id}, task {task_id}")

            return {
                "accessKeyId": credentials.access_key_id,
                "accessKeySecret": credentials.access_key_secret,
                "securityToken": credentials.security_token,
                "expiration": credentials.expiration
            }

        except Exception as e:
            logger.error(f"Failed to get STS credentials: {str(e)}")
            raise

    def _generate_upload_policy(self, task_id: str) -> str:
        """
        生成上传权限策略（可选，用于更精细的权限控制）

        Args:
            task_id: 任务 ID

        Returns:
            JSON 格式的权限策略
        """
        import json

        # 限制只能上传到特定路径
        resource = f"acs:oss:*:*:{settings.OSS_BUCKET_NAME}/{settings.OSS_SCENE_FOLDER}/*/{task_id}/*"

        policy = {
            "Version": "1",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "oss:PutObject",
                        "oss:InitiateMultipartUpload",
                        "oss:UploadPart",
                        "oss:UploadPartCopy",
                        "oss:CompleteMultipartUpload",
                        "oss:AbortMultipartUpload",
                        "oss:ListParts"
                    ],
                    "Resource": [resource]
                }
            ]
        }

        return json.dumps(policy)


# 创建全局 STS 服务实例
sts_service = STSService()
