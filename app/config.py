"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
from functools import lru_cache
import json


class Settings(BaseSettings):
    """应用配置类"""

    # Application
    APP_NAME: str = "YuntuServer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str
    REDIS_PASSWORD: str = ""

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30天 = 30 * 24 * 60 = 43200分钟
    REFRESH_TOKEN_EXPIRE_DAYS: int = 60  # 刷新令牌延长到60天

    # Aliyun OSS
    OSS_ACCESS_KEY_ID: str
    OSS_ACCESS_KEY_SECRET: str
    OSS_BUCKET_NAME: str
    OSS_ENDPOINT: str
    OSS_BASE_URL: str
    OSS_SCENE_FOLDER: str = "scenes"
    OSS_RESULT_FOLDER: str = "results"

    # Aliyun STS
    OSS_ROLE_ARN: str
    STS_ENDPOINT: str = "sts.cn-beijing.aliyuncs.com"

    # Aliyun SMS
    SMS_SIGN_NAME: str
    SMS_TEMPLATE_CODE: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Render Settings
    RENDER_SIMULATE_MODE: bool = True
    RENDER_FRAME_TIME_MIN: int = 2
    RENDER_FRAME_TIME_MAX: int = 5
    RENDER_COST_PER_FRAME: float = 0.5

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Domain
    DOMAIN: str = "api.yuntucv.com"

    # 微信开放平台配置（扫码登录）
    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_REDIRECT_URI: str = ""

    # 微信公众号配置（H5登录 - 可选）
    WECHAT_MP_APP_ID: str = ""
    WECHAT_MP_APP_SECRET: str = ""

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """解析 CORS_ORIGINS，支持从 .env 文件读取 JSON 字符串"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # 如果不是 JSON，尝试按逗号分割
                return [origin.strip() for origin in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
