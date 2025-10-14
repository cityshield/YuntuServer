"""
API v1 路由聚合
"""
from fastapi import APIRouter
from app.api.v1 import auth, files, users, tasks

api_router = APIRouter()

# 认证路由
api_router.include_router(auth.router)

# 文件路由
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# 用户路由
api_router.include_router(users.router)

# 任务路由
api_router.include_router(tasks.router)

# 临时的测试端点
@api_router.get("/ping")
async def ping():
    """测试端点"""
    return {"message": "pong"}
