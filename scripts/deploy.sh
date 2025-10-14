#!/bin/bash

###############################################################################
# 生产环境部署脚本
# 用途：使用Docker Compose部署生产环境
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
echo -e "${BLUE}  YuntuServer 生产环境部署脚本${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker${NC}"
    echo -e "${YELLOW}请先安装 Docker: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker Compose${NC}"
    echo -e "${YELLOW}请先安装 Docker Compose: https://docs.docker.com/compose/install/${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境检查通过${NC}"

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到 .env 文件${NC}"
    echo -e "${YELLOW}请先创建 .env 文件并配置环境变量${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 找到 .env 配置文件${NC}"

# 部署选项
echo ""
echo -e "${YELLOW}请选择部署操作:${NC}"
echo -e "  ${BLUE}1)${NC} 首次部署 (构建镜像并启动)"
echo -e "  ${BLUE}2)${NC} 更新部署 (重新构建并重启)"
echo -e "  ${BLUE}3)${NC} 启动服务"
echo -e "  ${BLUE}4)${NC} 停止服务"
echo -e "  ${BLUE}5)${NC} 重启服务"
echo -e "  ${BLUE}6)${NC} 查看服务状态"
echo -e "  ${BLUE}7)${NC} 查看服务日志"
echo -e "  ${BLUE}8)${NC} 清理服务 (删除容器和卷)"
echo -e "  ${BLUE}9)${NC} 数据库迁移"
echo ""

read -p "请输入选项 [1-9]: " choice

case $choice in
    1)
        echo -e "${GREEN}开始首次部署...${NC}"
        echo ""

        # 创建必要的目录
        echo -e "${BLUE}创建必要的目录...${NC}"
        mkdir -p logs uploads logs/nginx
        echo -e "${GREEN}✓ 目录创建完成${NC}"

        # 构建镜像
        echo -e "${BLUE}构建Docker镜像...${NC}"
        docker-compose -f docker/docker-compose.yml build --no-cache
        echo -e "${GREEN}✓ 镜像构建完成${NC}"

        # 启动服务
        echo -e "${BLUE}启动服务...${NC}"
        docker-compose -f docker/docker-compose.yml up -d
        echo -e "${GREEN}✓ 服务启动完成${NC}"

        # 等待服务就绪
        echo -e "${BLUE}等待服务启动...${NC}"
        sleep 10

        # 运行数据库迁移
        echo -e "${BLUE}运行数据库迁移...${NC}"
        docker-compose -f docker/docker-compose.yml exec -T api alembic upgrade head
        echo -e "${GREEN}✓ 数据库迁移完成${NC}"

        # 显示服务状态
        echo ""
        echo -e "${GREEN}======================================${NC}"
        echo -e "${GREEN}  部署完成！${NC}"
        echo -e "${GREEN}======================================${NC}"
        echo ""
        docker-compose -f docker/docker-compose.yml ps
        echo ""
        echo -e "${BLUE}服务访问地址:${NC}"
        echo -e "  API 文档:    ${GREEN}http://localhost/docs${NC}"
        echo -e "  Flower 监控: ${GREEN}http://localhost:5555${NC}"
        echo ""
        ;;

    2)
        echo -e "${GREEN}开始更新部署...${NC}"
        echo ""

        # 停止服务
        echo -e "${BLUE}停止现有服务...${NC}"
        docker-compose -f docker/docker-compose.yml down
        echo -e "${GREEN}✓ 服务已停止${NC}"

        # 重新构建镜像
        echo -e "${BLUE}重新构建Docker镜像...${NC}"
        docker-compose -f docker/docker-compose.yml build --no-cache
        echo -e "${GREEN}✓ 镜像构建完成${NC}"

        # 启动服务
        echo -e "${BLUE}启动服务...${NC}"
        docker-compose -f docker/docker-compose.yml up -d
        echo -e "${GREEN}✓ 服务启动完成${NC}"

        # 等待服务就绪
        echo -e "${BLUE}等待服务启动...${NC}"
        sleep 10

        # 运行数据库迁移
        echo -e "${BLUE}运行数据库迁移...${NC}"
        docker-compose -f docker/docker-compose.yml exec -T api alembic upgrade head
        echo -e "${GREEN}✓ 数据库迁移完成${NC}"

        # 显示服务状态
        echo ""
        echo -e "${GREEN}======================================${NC}"
        echo -e "${GREEN}  更新部署完成！${NC}"
        echo -e "${GREEN}======================================${NC}"
        echo ""
        docker-compose -f docker/docker-compose.yml ps
        ;;

    3)
        echo -e "${GREEN}启动服务...${NC}"
        docker-compose -f docker/docker-compose.yml up -d
        echo -e "${GREEN}✓ 服务启动完成${NC}"
        echo ""
        docker-compose -f docker/docker-compose.yml ps
        ;;

    4)
        echo -e "${YELLOW}停止服务...${NC}"
        docker-compose -f docker/docker-compose.yml down
        echo -e "${GREEN}✓ 服务已停止${NC}"
        ;;

    5)
        echo -e "${YELLOW}重启服务...${NC}"
        docker-compose -f docker/docker-compose.yml restart
        echo -e "${GREEN}✓ 服务已重启${NC}"
        echo ""
        docker-compose -f docker/docker-compose.yml ps
        ;;

    6)
        echo -e "${BLUE}服务状态:${NC}"
        echo ""
        docker-compose -f docker/docker-compose.yml ps
        echo ""
        echo -e "${BLUE}容器资源使用:${NC}"
        docker stats --no-stream $(docker-compose -f docker/docker-compose.yml ps -q)
        ;;

    7)
        echo -e "${YELLOW}请选择要查看的服务日志:${NC}"
        echo -e "  ${BLUE}1)${NC} API 服务"
        echo -e "  ${BLUE}2)${NC} Celery Worker"
        echo -e "  ${BLUE}3)${NC} Celery Beat"
        echo -e "  ${BLUE}4)${NC} Flower"
        echo -e "  ${BLUE}5)${NC} Nginx"
        echo -e "  ${BLUE}6)${NC} PostgreSQL"
        echo -e "  ${BLUE}7)${NC} Redis"
        echo -e "  ${BLUE}8)${NC} 所有服务"
        echo ""
        read -p "请输入选项 [1-8]: " log_choice

        case $log_choice in
            1) docker-compose -f docker/docker-compose.yml logs -f api ;;
            2) docker-compose -f docker/docker-compose.yml logs -f celery-worker ;;
            3) docker-compose -f docker/docker-compose.yml logs -f celery-beat ;;
            4) docker-compose -f docker/docker-compose.yml logs -f flower ;;
            5) docker-compose -f docker/docker-compose.yml logs -f nginx ;;
            6) docker-compose -f docker/docker-compose.yml logs -f postgres ;;
            7) docker-compose -f docker/docker-compose.yml logs -f redis ;;
            8) docker-compose -f docker/docker-compose.yml logs -f ;;
            *) echo -e "${RED}无效的选项${NC}" ;;
        esac
        ;;

    8)
        echo -e "${RED}警告: 此操作将删除所有容器和数据卷！${NC}"
        read -p "确定要继续吗? (yes/no): " confirm

        if [ "$confirm" = "yes" ]; then
            echo -e "${YELLOW}清理服务和数据...${NC}"
            docker-compose -f docker/docker-compose.yml down -v
            echo -e "${GREEN}✓ 清理完成${NC}"
        else
            echo -e "${YELLOW}已取消操作${NC}"
        fi
        ;;

    9)
        echo -e "${BLUE}运行数据库迁移...${NC}"
        docker-compose -f docker/docker-compose.yml exec api alembic upgrade head
        echo -e "${GREEN}✓ 数据库迁移完成${NC}"
        ;;

    *)
        echo -e "${RED}无效的选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}操作完成！${NC}"
