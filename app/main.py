"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.db.session import engine
from app.db.base import Base, import_models
from app.utils.logger import setup_logger

# 设置日志
logger = setup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # Startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📍 API URL: https://{settings.DOMAIN}{settings.API_V1_PREFIX}")

    # 导入所有模型
    import_models()

    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")

    yield

    # Shutdown
    logger.info("👋 Shutting down application")
    await engine.dispose()


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="盛世云图 Maya 云渲染平台后端服务",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip 压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由（将在后续创建）
from app.api.v1.router import api_router
from app.api import websocket

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(websocket.router, tags=["WebSocket"])


# 健康检查
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME,
        "domain": settings.DOMAIN,
    }


@app.get("/", tags=["Root"])
async def root():
    """根端点"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": f"https://{settings.DOMAIN}/docs" if settings.DEBUG else "disabled",
        "api": f"https://{settings.DOMAIN}{settings.API_V1_PREFIX}",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
