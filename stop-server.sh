#!/bin/bash

# YuntuServer 停止脚本
# 使用方法: ./stop-server.sh

echo "========================================="
echo "🛑 停止 YuntuServer (端口 8000)"
echo "========================================="

# 查找并终止在 8000 端口运行的进程
PIDS=$(lsof -ti:8000)

if [ -z "$PIDS" ]; then
    echo "✅ 没有在端口 8000 运行的服务"
else
    echo "📋 找到以下进程:"
    lsof -i:8000
    echo ""
    echo "🔪 终止进程..."
    kill -9 $PIDS
    echo "✅ YuntuServer 已停止"
fi

echo "========================================="
