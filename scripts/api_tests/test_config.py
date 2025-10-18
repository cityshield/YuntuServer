"""
配置 API 测试脚本

测试获取 OSS 配置功能

使用方法:
python scripts/api_tests/test_config.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

def print_section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_success(message: str):
    print(f"✅ {message}")

def print_error(message: str):
    print(f"❌ {message}")

def print_info(message: str):
    print(f"ℹ️  {message}")

def print_json(data: dict, title: str = "响应数据"):
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def login():
    """登录获取token"""
    print_section("步骤 1: 登录获取 Token")
    
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"username": "testuser_sms", "password": "testpass123"}
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print_success("登录成功")
        print_info(f"Token: {token[:50]}...")
        return token
    else:
        print_error(f"登录失败: {response.text}")
        return None

def test_get_oss_config(token: str):
    """测试获取 OSS 配置"""
    print_section("步骤 2: 获取 OSS 配置")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/config/oss",
        headers=headers
    )
    
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        config = response.json()
        print_json(config, "OSS 配置")
        
        # 验证配置完整性
        required_fields = ["access_key_id", "access_key_secret", "bucket_name", "endpoint", "base_url"]
        missing = [f for f in required_fields if not config.get(f)]
        
        if missing:
            print_error(f"配置不完整，缺少字段: {missing}")
            return False
        
        print_success("OSS 配置获取成功且完整")
        return True
    else:
        print_error(f"获取失败: {response.text}")
        return False

def main():
    print_section("开始配置 API 测试")
    
    # 检查服务器
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print_error(f"服务器状态异常，状态码: {health.status_code}")
            return
        print_success("服务器运行正常")
    except Exception as e:
        print_error(f"无法连接到服务器: {BASE_URL}")
        print_error(f"错误: {str(e)}")
        return
    
    # 登录
    token = login()
    if not token:
        print_error("登录失败，无法继续测试")
        return
    
    # 测试获取配置
    success = test_get_oss_config(token)
    
    # 结果
    print_section("测试结果")
    if success:
        print_success("所有测试通过！🎉")
    else:
        print_error("测试失败")

if __name__ == "__main__":
    main()
