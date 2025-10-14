"""
短信验证码服务
"""
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from loguru import logger

from app.config import settings
from app.core.cache import cache


class SMSService:
    """短信服务"""

    def __init__(self):
        """初始化短信客户端"""
        self.demo_mode = settings.DEBUG  # 开发模式使用演示模式

        if not self.demo_mode:
            config = open_api_models.Config(
                access_key_id=settings.OSS_ACCESS_KEY_ID,
                access_key_secret=settings.OSS_ACCESS_KEY_SECRET
            )
            # 短信服务的endpoint固定为dysmsapi.aliyuncs.com
            config.endpoint = 'dysmsapi.aliyuncs.com'
            self.client = Dysmsapi20170525Client(config)
        else:
            self.client = None
            logger.info("SMS Service initialized in DEMO mode - using fixed code '123456'")

        logger.info(f"SMS Service initialized (demo_mode={self.demo_mode})")

    def generate_code(self, length: int = 6) -> str:
        """生成验证码"""
        return ''.join(random.choices(string.digits, k=length))

    async def send_verification_code(self, phone: str) -> Dict[str, any]:
        """
        发送验证码

        Args:
            phone: 手机号

        Returns:
            dict: 发送结果
        """
        # 检查是否在60秒内已发送过
        cache_key = f"sms:sent:{phone}"
        if await cache.get(cache_key):
            return {
                "success": False,
                "message": "验证码已发送，请60秒后再试"
            }

        # 生成验证码
        if self.demo_mode:
            code = "123456"  # 演示模式使用固定验证码
            logger.info(f"[DEMO MODE] SMS code for {phone}: {code}")
        else:
            code = self.generate_code()

        try:
            # 演示模式：直接跳过真实发送
            if self.demo_mode:
                logger.info(f"[DEMO MODE] Simulating SMS sent to {phone}, code: {code}")
                success = True
                message = "验证码已发送（演示模式）"
                request_id = "demo_request_id"
            else:
                # 真实模式：调用阿里云SMS API
                send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
                    phone_numbers=phone,
                    sign_name=settings.SMS_SIGN_NAME,
                    template_code=settings.SMS_TEMPLATE_CODE,
                    template_param=f'{{"code":"{code}"}}'
                )

                response = self.client.send_sms(send_sms_request)
                logger.info(f"SMS sent to {phone}, code: {code}, response: {response.body.code}")

                success = response.body.code == 'OK'
                message = "验证码已发送" if success else f"发送失败: {response.body.message}"
                request_id = response.body.request_id

            if success:
                # 保存验证码到缓存（30分钟有效期）
                code_cache_key = f"sms:code:{phone}"
                await cache.set(code_cache_key, code, expire=1800)  # 30分钟

                # 设置60秒的发送间隔限制
                await cache.set(cache_key, "1", expire=60)

                return {
                    "success": True,
                    "message": message,
                    "request_id": request_id
                }
            else:
                logger.error(f"SMS send failed: {message}")
                return {
                    "success": False,
                    "message": message
                }

        except Exception as e:
            logger.error(f"SMS send error: {str(e)}")
            return {
                "success": False,
                "message": f"发送失败: {str(e)}"
            }

    async def verify_code(self, phone: str, code: str) -> bool:
        """
        验证验证码

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            bool: 是否验证成功
        """
        cache_key = f"sms:code:{phone}"
        cached_code = await cache.get(cache_key)

        if not cached_code:
            logger.warning(f"Verification code expired or not found for {phone}")
            return False

        if cached_code == code:
            # 验证成功后删除验证码
            await cache.delete(cache_key)
            logger.info(f"Verification code verified successfully for {phone}")
            return True

        logger.warning(f"Verification code mismatch for {phone}")
        return False

    async def get_remaining_time(self, phone: str) -> Optional[int]:
        """
        获取验证码剩余有效时间（秒）

        Args:
            phone: 手机号

        Returns:
            int: 剩余秒数，None表示验证码不存在
        """
        cache_key = f"sms:code:{phone}"
        ttl = await cache.ttl(cache_key)
        return ttl if ttl > 0 else None


# 创建全局实例
sms_service = SMSService()
