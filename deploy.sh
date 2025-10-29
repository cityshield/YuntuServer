#!/bin/bash

# ========================================
# YuntuServer 生产环境部署脚本
# ========================================
# 用途：将本地代码部署到阿里云服务器
# 目标目录：/var/www/api/
# 域名：api.yuntucv.com
# ========================================

set -e  # 遇到错误立即退出

# 配置变量
SERVER_USER="root"  # 修改为您的服务器用户名
SERVER_HOST="api.yuntucv.com"  # 服务器地址
DEPLOY_DIR="/var/www/api"  # 部署目录
APP_NAME="yuntu-server"  # 应用名称
SERVICE_NAME="yuntu-server"  # Systemd 服务名

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}开始部署 YuntuServer 到生产环境${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. 检查必要文件
echo -e "${YELLOW}[1/8] 检查必要文件...${NC}"
if [ ! -f ".env.production" ]; then
    echo -e "${RED}错误: .env.production 文件不存在${NC}"
    echo -e "${YELLOW}请先复制 .env.production.example 为 .env.production 并填入真实配置${NC}"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: requirements.txt 文件不存在${NC}"
    exit 1
fi

# 2. 打包项目文件
echo -e "${YELLOW}[2/8] 打包项目文件...${NC}"
tar -czf yuntu-server.tar.gz \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.db' \
    --exclude='*.db-journal' \
    --exclude='logs' \
    --exclude='temp_uploads' \
    --exclude='.pytest_cache' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    app/ alembic/ scripts/ \
    requirements.txt alembic.ini .env.production

echo -e "${GREEN}✓ 项目文件打包完成: yuntu-server.tar.gz${NC}"

# 3. 上传到服务器
echo -e "${YELLOW}[3/8] 上传文件到服务器...${NC}"
scp yuntu-server.tar.gz ${SERVER_USER}@${SERVER_HOST}:/tmp/

echo -e "${GREEN}✓ 文件上传完成${NC}"

# 4. 在服务器上执行部署
echo -e "${YELLOW}[4/8] 在服务器上执行部署...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'

set -e

# 配置变量
DEPLOY_DIR="/var/www/api"
SERVICE_NAME="yuntu-server"

echo "=========================================="
echo "服务器端部署开始"
echo "=========================================="

# 创建部署目录
echo "[服务器] 创建部署目录..."
mkdir -p ${DEPLOY_DIR}
cd ${DEPLOY_DIR}

# 备份当前版本（如果存在）
if [ -d "app" ]; then
    echo "[服务器] 备份当前版本..."
    BACKUP_DIR="${DEPLOY_DIR}/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p ${BACKUP_DIR}
    cp -r app alembic requirements.txt alembic.ini .env ${BACKUP_DIR}/ 2>/dev/null || true
    echo "✓ 备份完成: ${BACKUP_DIR}"
fi

# 解压新版本
echo "[服务器] 解压新版本..."
tar -xzf /tmp/yuntu-server.tar.gz -C ${DEPLOY_DIR}

# 重命名 .env.production 为 .env
if [ -f ".env.production" ]; then
    mv .env.production .env
    echo "✓ 配置文件就绪"
fi

# 创建日志目录
echo "[服务器] 创建日志目录..."
mkdir -p ${DEPLOY_DIR}/logs
chmod 755 ${DEPLOY_DIR}/logs

# 安装 Python 虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "[服务器] 创建 Python 虚拟环境..."
    python3 -m venv venv
    echo "✓ 虚拟环境创建完成"
fi

# 激活虚拟环境并安装依赖
echo "[服务器] 安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ 依赖安装完成"

# 运行数据库迁移
echo "[服务器] 运行数据库迁移..."
alembic upgrade head
echo "✓ 数据库迁移完成"

# 设置文件权限
echo "[服务器] 设置文件权限..."
chown -R www-data:www-data ${DEPLOY_DIR}
chmod -R 755 ${DEPLOY_DIR}
echo "✓ 权限设置完成"

# 重启服务
echo "[服务器] 重启应用服务..."
if systemctl is-active --quiet ${SERVICE_NAME}; then
    systemctl restart ${SERVICE_NAME}
    echo "✓ 服务已重启"
else
    systemctl start ${SERVICE_NAME}
    echo "✓ 服务已启动"
fi

# 检查服务状态
sleep 3
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "✓ 服务运行正常"
else
    echo "✗ 服务启动失败，请检查日志"
    exit 1
fi

# 清理临时文件
rm -f /tmp/yuntu-server.tar.gz

echo "=========================================="
echo "服务器端部署完成"
echo "=========================================="

ENDSSH

# 5. 清理本地临时文件
echo -e "${YELLOW}[5/8] 清理本地临时文件...${NC}"
rm -f yuntu-server.tar.gz
echo -e "${GREEN}✓ 清理完成${NC}"

# 6. 检查服务状态
echo -e "${YELLOW}[6/8] 检查服务状态...${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "systemctl status ${SERVICE_NAME} --no-pager"

# 7. 测试健康检查接口
echo -e "${YELLOW}[7/8] 测试健康检查接口...${NC}"
sleep 2
if curl -s https://${SERVER_HOST}/health | grep -q "healthy"; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${YELLOW}警告: 健康检查失败，请手动检查${NC}"
fi

# 8. 完成
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "应用地址: https://${SERVER_HOST}"
echo -e "健康检查: https://${SERVER_HOST}/health"
echo -e "API 文档: https://${SERVER_HOST}/docs"
echo -e ""
echo -e "查看日志: ssh ${SERVER_USER}@${SERVER_HOST} \"tail -f ${DEPLOY_DIR}/logs/app.log\""
echo -e "查看服务状态: ssh ${SERVER_USER}@${SERVER_HOST} \"systemctl status ${SERVICE_NAME}\""
echo -e "${GREEN}========================================${NC}"
