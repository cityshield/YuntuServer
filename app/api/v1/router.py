"""
API v1 路由聚合
"""
from fastapi import APIRouter
from app.api.v1 import auth, files, users, tasks, logs, config, wechat, drives, upload_tasks, file_uploads, oss_callback

api_router = APIRouter()

# 认证路由
api_router.include_router(auth.router)

# 微信登录路由
api_router.include_router(wechat.router)

# 盘符路由
api_router.include_router(drives.router)

# 上传任务路由
api_router.include_router(upload_tasks.router)

# 文件上传路由
api_router.include_router(file_uploads.router)

# OSS 回调路由（无需认证，OSS 直接调用）
api_router.include_router(oss_callback.router)

# 文件路由
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# 用户路由
api_router.include_router(users.router)

# 任务路由
api_router.include_router(tasks.router)

# 日志路由
api_router.include_router(logs.router)

# 配置路由
api_router.include_router(config.router)

# 临时的测试端点
@api_router.get("/ping")
async def ping():
    """测试端点"""
    return {"message": "pong"}
