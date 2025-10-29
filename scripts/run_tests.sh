#!/bin/bash

# 测试运行脚本
# 提供多种测试选项

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}       YuntuServer 测试套件运行脚本${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}错误: 未找到虚拟环境${NC}"
    echo -e "${YELLOW}请先运行: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}错误: pytest未安装${NC}"
    echo -e "${YELLOW}请运行: pip install -r requirements.txt${NC}"
    exit 1
fi

# 菜单
echo -e "${GREEN}请选择测试模式:${NC}"
echo "1. 运行所有测试"
echo "2. 运行认证API测试"
echo "3. 运行用户API测试"
echo "4. 运行任务API测试"
echo "5. 运行文件API测试"
echo "6. 运行测试并生成覆盖率报告"
echo "7. 运行特定测试文件"
echo "8. 运行特定测试用例"
echo "9. 快速测试(不生成报告)"
echo "0. 退出"
echo ""

read -p "请输入选项 (0-9): " choice

case $choice in
    1)
        echo -e "${GREEN}运行所有测试...${NC}"
        pytest app/tests/ -v
        ;;
    2)
        echo -e "${GREEN}运行认证API测试...${NC}"
        pytest app/tests/test_auth.py -v -m auth
        ;;
    3)
        echo -e "${GREEN}运行用户API测试...${NC}"
        pytest app/tests/test_users.py -v -m user
        ;;
    4)
        echo -e "${GREEN}运行任务API测试...${NC}"
        pytest app/tests/test_tasks.py -v -m task
        ;;
    5)
        echo -e "${GREEN}运行文件API测试...${NC}"
        pytest app/tests/test_files.py -v -m file
        ;;
    6)
        echo -e "${GREEN}运行测试并生成覆盖率报告...${NC}"
        pytest app/tests/ -v --cov=app --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"

        # 询问是否打开报告
        read -p "是否打开覆盖率报告? (y/n): " open_report
        if [ "$open_report" = "y" ] || [ "$open_report" = "Y" ]; then
            if command -v open &> /dev/null; then
                open htmlcov/index.html
            elif command -v xdg-open &> /dev/null; then
                xdg-open htmlcov/index.html
            else
                echo -e "${YELLOW}请手动打开: htmlcov/index.html${NC}"
            fi
        fi
        ;;
    7)
        echo -e "${YELLOW}可用的测试文件:${NC}"
        echo "- app/tests/test_auth.py"
        echo "- app/tests/test_users.py"
        echo "- app/tests/test_tasks.py"
        echo "- app/tests/test_files.py"
        echo ""
        read -p "请输入测试文件路径: " test_file
        pytest "$test_file" -v
        ;;
    8)
        echo -e "${YELLOW}示例: TestAuthLogin::test_login_with_username_success${NC}"
        read -p "请输入测试用例名称: " test_case
        pytest app/tests/ -v -k "$test_case"
        ;;
    9)
        echo -e "${GREEN}运行快速测试(无覆盖率)...${NC}"
        pytest app/tests/ -v --no-cov
        ;;
    0)
        echo -e "${YELLOW}退出测试脚本${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}无效选项!${NC}"
        exit 1
        ;;
esac

# 检查测试结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}==================================================${NC}"
    echo -e "${GREEN}            ✅ 测试通过!${NC}"
    echo -e "${GREEN}==================================================${NC}"
else
    echo ""
    echo -e "${RED}==================================================${NC}"
    echo -e "${RED}            ❌ 测试失败!${NC}"
    echo -e "${RED}==================================================${NC}"
    exit 1
fi
