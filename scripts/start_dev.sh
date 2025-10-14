#!/bin/bash

###############################################################################
# 开发环境启动脚本
# 用途：启动本地开发环境（不使用Docker）
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  YuntuServer 开发环境启动脚本${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到 .env 文件${NC}"
    echo -e "${YELLOW}请先创建 .env 文件并配置环境变量${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 找到 .env 配置文件${NC}"

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}未找到虚拟环境，正在创建...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo -e "${BLUE}激活虚拟环境...${NC}"
source venv/bin/activate

# 安装/更新依赖
echo -e "${BLUE}检查并安装依赖...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# 创建必要的目录
echo -e "${BLUE}创建必要的目录...${NC}"
mkdir -p logs uploads
echo -e "${GREEN}✓ 目录创建完成${NC}"

# 检查PostgreSQL连接
echo -e "${BLUE}检查数据库连接...${NC}"
if python -c "
from app.config import settings
from sqlalchemy import create_engine
import sys

try:
    # 使用同步引擎测试连接
    sync_url = settings.DATABASE_URL.replace('+asyncpg', '')
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        pass
    print('✓ 数据库连接成功')
    sys.exit(0)
except Exception as e:
    print(f'✗ 数据库连接失败: {e}')
    sys.exit(1)
"; then
    echo -e "${GREEN}✓ 数据库连接正常${NC}"
else
    echo -e "${RED}✗ 数据库连接失败${NC}"
    echo -e "${YELLOW}请检查 PostgreSQL 是否运行，以及 .env 中的 DATABASE_URL 配置${NC}"
    exit 1
fi

# 检查Redis连接
echo -e "${BLUE}检查Redis连接...${NC}"
if python -c "
from app.config import settings
import redis
import sys

try:
    r = redis.from_url(settings.REDIS_URL, password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None)
    r.ping()
    print('✓ Redis连接成功')
    sys.exit(0)
except Exception as e:
    print(f'✗ Redis连接失败: {e}')
    sys.exit(1)
"; then
    echo -e "${GREEN}✓ Redis连接正常${NC}"
else
    echo -e "${RED}✗ Redis连接失败${NC}"
    echo -e "${YELLOW}请检查 Redis 是否运行，以及 .env 中的 REDIS_URL 配置${NC}"
    exit 1
fi

# 运行数据库迁移
echo -e "${BLUE}运行数据库迁移...${NC}"
alembic upgrade head
echo -e "${GREEN}✓ 数据库迁移完成${NC}"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  环境检查完成，准备启动服务${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# 启动方式选择
echo -e "${YELLOW}请选择启动方式:${NC}"
echo -e "  ${BLUE}1)${NC} 启动 FastAPI 服务"
echo -e "  ${BLUE}2)${NC} 启动 Celery Worker"
echo -e "  ${BLUE}3)${NC} 启动 Celery Beat"
echo -e "  ${BLUE}4)${NC} 启动 Flower 监控"
echo -e "  ${BLUE}5)${NC} 启动全部服务 (推荐)"
echo ""

read -p "请输入选项 [1-5]: " choice

case $choice in
    1)
        echo -e "${GREEN}启动 FastAPI 服务...${NC}"
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    2)
        echo -e "${GREEN}启动 Celery Worker...${NC}"
        celery -A app.tasks.celery_app worker --loglevel=info --queues=render --concurrency=2
        ;;
    3)
        echo -e "${GREEN}启动 Celery Beat...${NC}"
        celery -A app.tasks.celery_app beat --loglevel=info
        ;;
    4)
        echo -e "${GREEN}启动 Flower 监控...${NC}"
        celery -A app.tasks.celery_app flower --port=5555
        ;;
    5)
        echo -e "${GREEN}启动全部服务...${NC}"
        echo -e "${YELLOW}注意: 将在后台启动 Celery Worker 和 Beat${NC}"
        echo -e "${YELLOW}      FastAPI 服务将在前台运行${NC}"
        echo ""

        # 启动 Celery Worker (后台)
        celery -A app.tasks.celery_app worker --loglevel=info --queues=render --concurrency=2 \
            --pidfile=logs/celery_worker.pid --logfile=logs/celery_worker.log --detach
        echo -e "${GREEN}✓ Celery Worker 已启动 (PID: $(cat logs/celery_worker.pid))${NC}"

        # 启动 Celery Beat (后台)
        celery -A app.tasks.celery_app beat --loglevel=info \
            --pidfile=logs/celery_beat.pid --logfile=logs/celery_beat.log --detach
        echo -e "${GREEN}✓ Celery Beat 已启动 (PID: $(cat logs/celery_beat.pid))${NC}"

        # 启动 Flower (后台)
        celery -A app.tasks.celery_app flower --port=5555 \
            --pidfile=logs/flower.pid --logfile=logs/flower.log --detach
        echo -e "${GREEN}✓ Flower 监控已启动 (PID: $(cat logs/flower.pid))${NC}"

        echo ""
        echo -e "${BLUE}服务访问地址:${NC}"
        echo -e "  FastAPI 文档: ${GREEN}http://localhost:8000/docs${NC}"
        echo -e "  Flower 监控:  ${GREEN}http://localhost:5555${NC}"
        echo ""
        echo -e "${YELLOW}按 Ctrl+C 停止 FastAPI 服务${NC}"
        echo -e "${YELLOW}运行以下命令停止后台服务:${NC}"
        echo -e "  kill \$(cat logs/celery_worker.pid)"
        echo -e "  kill \$(cat logs/celery_beat.pid)"
        echo -e "  kill \$(cat logs/flower.pid)"
        echo ""

        # 启动 FastAPI (前台)
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    *)
        echo -e "${RED}无效的选项${NC}"
        exit 1
        ;;
esac
