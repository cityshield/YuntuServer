"""
认证 API 测试脚本

测试功能：
1. 发送短信验证码
2. 用户注册（使用验证码）
3. 用户登录（用户名/密码）
4. Token 刷新
5. 用户登出

使用方法:
python scripts/api_tests/test_auth.py
"""

import os
import sys
import json
import random
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 加载环境变量
load_dotenv()

# ==================== 配置 ====================

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# ==================== 辅助函数 ====================

def print_section(title: str):
    """打印分隔线和标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_success(message: str):
    print(f"✅ {message}")

def print_error(message: str):
    print(f"❌ {message}")

def print_info(message: str):
    print(f"ℹ️  {message}")

def print_json(data: Dict[str, Any], title: str = "响应数据"):
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> requests.Response:
    """发送 HTTP 请求"""
    url = f"{BASE_URL}{API_PREFIX}{endpoint}"
    
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)
    
    print_info(f"请求: {method} {url}")
    if data:
        print(f"请求数据: {json.dumps(data, ensure_ascii=False)}")
    
    response = requests.request(
        method=method,
        url=url,
        json=data,
        headers=default_headers,
        timeout=30
    )
    
    print(f"状态码: {response.status_code}")
    return response

# ==================== 测试函数 ====================

def test_send_verification_code():
    """测试发送验证码"""
    print_section("测试 1: 发送短信验证码")
    
    # 生成随机手机号（测试用）
    phone = f"138{random.randint(10000000, 99999999)}"
    
    response = make_request(
        method="POST",
        endpoint="/auth/send-code",
        data={"phone": phone}
    )
    
    if response.status_code == 200:
        result = response.json()
        print_json(result)
        
        if result.get("success"):
            print_success(f"验证码发送成功！手机号: {phone}")
            print_info("演示模式下验证码为: 123456")
            return True, phone
        else:
            print_error(f"发送失败: {result.get('message')}")
            return False, None
    else:
        print_error(f"请求失败: {response.text}")
        return False, None

def test_register(phone: str = None):
    """测试用户注册"""
    print_section("测试 2: 用户注册")
    
    # 如果没有提供手机号，先发送验证码
    if not phone:
        success, phone = test_send_verification_code()
        if not success:
            return False, None
    
    # 生成随机用户名
    username = f"testuser_{random.randint(1000, 9999)}"
    
    register_data = {
        "username": username,
        "phone": phone,
        "verification_code": "123456",  # 演示模式固定验证码
        "password": "testpass123",
        "email": f"{username}@test.com"
    }
    
    response = make_request(
        method="POST",
        endpoint="/auth/register",
        data=register_data
    )
    
    if response.status_code == 201:
        result = response.json()
        print_json(result)
        
        user = result.get("user")
        access_token = result.get("access_token")
        
        print_success(f"注册成功！")
        print_info(f"用户ID: {user.get('id')}")
        print_info(f"用户名: {user.get('username')}")
        print_info(f"手机号: {user.get('phone')}")
        
        return True, {
            "username": username,
            "password": "testpass123",
            "access_token": access_token,
            "refresh_token": result.get("refresh_token")
        }
    else:
        print_error(f"注册失败: {response.text}")
        return False, None

def test_login(username: str, password: str):
    """测试用户登录"""
    print_section("测试 3: 用户登录")
    
    login_data = {
        "username": username,
        "password": password
    }
    
    response = make_request(
        method="POST",
        endpoint="/auth/login",
        data=login_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print_json(result)
        
        user = result.get("user")
        access_token = result.get("access_token")
        
        print_success("登录成功！")
        print_info(f"用户: {user.get('username')}")
        print_info(f"Token: {access_token[:50]}...")
        
        return True, {
            "access_token": access_token,
            "refresh_token": result.get("refresh_token")
        }
    else:
        print_error(f"登录失败: {response.text}")
        return False, None

def test_refresh_token(refresh_token: str):
    """测试刷新 Token"""
    print_section("测试 4: 刷新访问令牌")
    
    response = make_request(
        method="POST",
        endpoint="/auth/refresh",
        data={"refresh_token": refresh_token}
    )
    
    if response.status_code == 200:
        result = response.json()
        print_json(result)
        
        new_access_token = result.get("access_token")
        print_success("Token 刷新成功！")
        print_info(f"新 Token: {new_access_token[:50]}...")
        
        return True, new_access_token
    else:
        print_error(f"刷新失败: {response.text}")
        return False, None

def test_logout(refresh_token: str):
    """测试登出"""
    print_section("测试 5: 用户登出")
    
    response = make_request(
        method="POST",
        endpoint="/auth/logout",
        data={"refresh_token": refresh_token}
    )
    
    if response.status_code == 200:
        result = response.json()
        print_json(result)
        print_success("登出成功！")
        return True
    else:
        print_error(f"登出失败: {response.text}")
        return False

def test_protected_endpoint(access_token: str):
    """测试受保护的端点（需要认证）"""
    print_section("额外测试: 访问受保护端点")
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = make_request(
        method="GET",
        endpoint="/users/me",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print_json(result, "当前用户信息")
        print_success("认证成功，可以访问受保护的端点")
        return True
    else:
        print_error(f"访问失败: {response.text}")
        return False

# ==================== 主函数 ====================

def main():
    """完整的认证流程测试"""
    print_section("开始认证 API 测试")
    
    # 检查服务器
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
    
    # 执行测试流程
    results = []
    
    # 1. 注册新用户
    success, user_data = test_register()
    results.append(("用户注册", success))
    
    if not success:
        print_error("注册失败，终止测试")
        return
    
    # 2. 使用注册的账号登录
    success, tokens = test_login(user_data["username"], user_data["password"])
    results.append(("用户登录", success))
    
    if success:
        # 3. 测试受保护端点
        success = test_protected_endpoint(tokens["access_token"])
        results.append(("访问受保护端点", success))
        
        # 4. 刷新 Token
        success, new_token = test_refresh_token(tokens["refresh_token"])
        results.append(("刷新Token", success))
        
        # 5. 登出
        success = test_logout(tokens["refresh_token"])
        results.append(("用户登出", success))
    
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
