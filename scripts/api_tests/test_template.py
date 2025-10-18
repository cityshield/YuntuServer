"""
API 测试脚本模板

这是一个标准的 API 测试脚本模板，用于快速创建新的测试脚本。

使用方法：
1. 复制此文件并重命名为 test_<功能名>.py
2. 修改模块说明和配置
3. 实现测试函数
4. 运行: python scripts/api_tests/test_<功能名>.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 加载环境变量
load_dotenv()

# ==================== 配置区域 ====================

# API 基础 URL
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# 其他配置（根据需要添加）
# ACCESS_KEY = os.getenv("OSS_ACCESS_KEY_ID")
# SECRET_KEY = os.getenv("OSS_ACCESS_KEY_SECRET")

# ==================== 辅助函数 ====================

def print_section(title: str):
    """打印分隔线和标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_success(message: str):
    """打印成功消息"""
    print(f"✅ {message}")

def print_error(message: str):
    """打印错误消息"""
    print(f"❌ {message}")

def print_info(message: str):
    """打印信息消息"""
    print(f"ℹ️  {message}")

def print_json(data: Dict[str, Any], title: str = "响应数据"):
    """格式化打印 JSON 数据"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> requests.Response:
    """
    发送 HTTP 请求
    
    Args:
        method: 请求方法 (GET, POST, PUT, DELETE)
        endpoint: API 端点 (例如: /auth/login)
        data: 请求体数据 (JSON)
        headers: 请求头
        params: URL 参数
    
    Returns:
        Response 对象
    """
    url = f"{BASE_URL}{API_PREFIX}{endpoint}"
    
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    print_info(f"请求: {method} {url}")
    if data:
        print(f"请求数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=default_headers,
            params=params,
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        return response
        
    except requests.exceptions.RequestException as e:
        print_error(f"请求失败: {str(e)}")
        raise

# ==================== 测试函数 ====================

def test_example():
    """示例测试函数"""
    print_section("示例测试")
    
    try:
        # 1. 准备测试数据
        test_data = {
            "key": "value"
        }
        
        # 2. 发送请求
        response = make_request(
            method="POST",
            endpoint="/example",
            data=test_data
        )
        
        # 3. 验证响应
        if response.status_code == 200:
            result = response.json()
            print_json(result)
            print_success("测试通过！")
            return True
        else:
            print_error(f"请求失败: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_with_auth():
    """需要认证的测试示例"""
    print_section("认证测试")
    
    # 1. 先登录获取 Token
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    
    login_response = make_request(
        method="POST",
        endpoint="/auth/login",
        data=login_data
    )
    
    if login_response.status_code != 200:
        print_error("登录失败")
        return False
    
    # 2. 获取 access_token
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        print_error("未获取到 access_token")
        return False
    
    print_success("登录成功，获取到 Token")
    
    # 3. 使用 Token 访问需要认证的接口
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = make_request(
        method="GET",
        endpoint="/users/me",
        headers=headers
    )
    
    if response.status_code == 200:
        user_data = response.json()
        print_json(user_data, "用户信息")
        print_success("认证测试通过！")
        return True
    else:
        print_error(f"请求失败: {response.text}")
        return False

# ==================== 主函数 ====================

def main():
    """主测试流程"""
    print_section("开始 API 测试")
    
    # 检查服务器是否运行
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print_success("服务器运行正常")
        else:
            print_error("服务器状态异常")
            return
    except requests.exceptions.RequestException:
        print_error(f"无法连接到服务器: {BASE_URL}")
        print_info("请确保服务器已启动: uvicorn app.main:app --reload")
        return
    
    # 运行测试
    tests = [
        ("示例测试", test_example),
        ("认证测试", test_with_auth),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"{test_name} 执行失败: {str(e)}")
            results.append((test_name, False))
    
    # 打印测试结果汇总
    print_section("测试结果汇总")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print_success("所有测试通过！🎉")
    else:
        print_error(f"有 {total - passed} 个测试失败")

if __name__ == "__main__":
    main()
