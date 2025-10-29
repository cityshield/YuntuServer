#!/bin/bash

# YuntuServer 启动脚本 - 固定端口 8000
# 使用方法: ./start-server.sh

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Pydantic Settings 会自动从 .env 文件加载配置，无需手动导出
# 这里只设置 uvicorn 命令行参数的默认值
PORT=8000
HOST=0.0.0.0

echo "========================================="
echo "🚀 启动 YuntuServer"
echo "========================================="
echo "端口: $PORT"
echo "主机: $HOST"
echo "目录: $SCRIPT_DIR"
echo "========================================="

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 错误: 未找到虚拟环境 venv/"
    echo "请先创建虚拟环境: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境并启动服务
source venv/bin/activate

echo "✅ 虚拟环境已激活"
echo "📦 启动 uvicorn 服务器..."
echo ""

# 启动 uvicorn
uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
