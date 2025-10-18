"""
配置相关的 API 端点
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/config", tags=["配置"])


class OSSConfigResponse(BaseModel):
    """OSS 配置响应"""
    access_key_id: str
    access_key_secret: str
    bucket_name: str
    endpoint: str
    base_url: str


@router.get(
    "/oss",
    response_model=OSSConfigResponse,
    summary="获取 OSS 配置",
    description="获取阿里云 OSS 上传所需的配置信息（需要登录）",
)
async def get_oss_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 OSS 配置
    
    返回客户端上传文件到 OSS 所需的配置信息
    """
    return OSSConfigResponse(
        access_key_id=settings.OSS_ACCESS_KEY_ID,
        access_key_secret=settings.OSS_ACCESS_KEY_SECRET,
        bucket_name=settings.OSS_BUCKET_NAME,
        endpoint=settings.OSS_ENDPOINT,
        base_url=settings.OSS_BASE_URL,
    )
