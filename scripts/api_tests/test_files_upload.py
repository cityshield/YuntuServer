"""
文件上传 API 测试脚本

测试功能：
1. 上传文件到 OSS
2. 获取下载 URL
3. 获取文件信息
4. 删除文件（可选）

使用方法:
python scripts/api_tests/test_files_upload.py              # 完整测试（包含删除）
python scripts/api_tests/test_files_upload.py --no-cleanup # 保留文件不删除
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from uuid import uuid4
import tempfile
import argparse

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
    headers: Optional[Dict] = None,
    files: Optional[Dict] = None
) -> requests.Response:
    """发送 HTTP 请求"""
    url = f"{BASE_URL}{API_PREFIX}{endpoint}"

    default_headers = {}
    if headers:
        default_headers.update(headers)

    print_info(f"请求: {method} {url}")
    if data and not files:
        print(f"请求数据: {json.dumps(data, ensure_ascii=False)}")

    try:
        if files:
            # 文件上传不设置 Content-Type，让 requests 自动设置
            response = requests.request(
                method=method,
                url=url,
                files=files,
                headers=default_headers,
                timeout=30
            )
        else:
            # JSON 请求
            if data:
                default_headers["Content-Type"] = "application/json"
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=default_headers,
                timeout=30
            )

        print(f"状态码: {response.status_code}")
        return response

    except requests.exceptions.RequestException as e:
        print_error(f"请求失败: {str(e)}")
        raise

# ==================== 测试函数 ====================

def login():
    """登录获取token"""
    print_section("步骤 1: 登录获取 Token")

    response = make_request(
        method="POST",
        endpoint="/auth/login",
        data={"username": "testuser_sms", "password": "testpass123"}
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

def create_test_file():
    """创建测试文件"""
    print_section("步骤 2: 创建测试文件")

    # 创建临时测试文件
    test_content = """//Maya ASCII scene
//Name: test_scene.ma
//Last modified: 2025-10-18

requires maya "2023";
currentUnit -l centimeter -a degree -t film;

// 这是一个测试用的 Maya 场景文件
// 包含简单的立方体对象

createNode transform -n "pCube1";
createNode mesh -n "pCubeShape1" -p "pCube1";
    setAttr ".v" yes;
    setAttr ".vir" yes;
    setAttr ".vif" yes;

// End of test_scene.ma
"""

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.ma',
        prefix='test_scene_',
        delete=False,
        encoding='utf-8'
    )

    temp_file.write(test_content)
    temp_file.close()

    file_size = os.path.getsize(temp_file.name)
    print_success(f"测试文件创建成功")
    print_info(f"文件路径: {temp_file.name}")
    print_info(f"文件大小: {file_size} 字节")

    return temp_file.name

def test_upload_file(token: str, task_id: str, file_path: str):
    """测试上传文件"""
    print_section("步骤 3: 上传文件到 OSS")

    headers = {"Authorization": f"Bearer {token}"}

    # 准备文件
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        files = {
            'file': (filename, f, 'application/octet-stream')
        }

        # 构造 URL（包含 task_id 作为查询参数）
        url = f"{BASE_URL}{API_PREFIX}/files/upload?task_id={task_id}"
        print_info(f"上传 URL: {url}")
        print_info(f"文件名: {filename}")

        try:
            response = requests.post(
                url,
                headers=headers,
                files=files,
                timeout=60
            )

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print_json(result, "上传响应")

                if 'filename' in result or 'object_key' in result:
                    print_success("文件上传成功")
                    return True, result
                else:
                    print_error("响应格式不正确")
                    return False, None
            else:
                print_error(f"上传失败: {response.text}")
                return False, None

        except Exception as e:
            print_error(f"上传异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, None

def test_get_download_url(token: str, task_id: str, filename: str):
    """测试获取下载 URL"""
    print_section("步骤 4: 获取文件下载 URL")

    headers = {"Authorization": f"Bearer {token}"}

    response = make_request(
        method="GET",
        endpoint=f"/files/download/{task_id}/{filename}",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print_json(result, "下载 URL 响应")
        print_success("获取下载 URL 成功")
        return True, result
    else:
        print_error(f"获取下载 URL 失败: {response.text}")
        return False, None

def test_get_file_info(token: str, object_key: str):
    """测试获取文件信息"""
    print_section("步骤 5: 获取文件信息")

    headers = {"Authorization": f"Bearer {token}"}

    # URL 编码 object_key
    import urllib.parse
    encoded_key = urllib.parse.quote(object_key, safe='')

    response = make_request(
        method="GET",
        endpoint=f"/files/info/{encoded_key}",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print_json(result, "文件信息")
        print_success("获取文件信息成功")
        return True, result
    else:
        print_error(f"获取文件信息失败: {response.text}")
        return False, None

def test_delete_file(token: str, object_key: str):
    """测试删除文件"""
    print_section("步骤 6: 删除测试文件（清理）")

    headers = {"Authorization": f"Bearer {token}"}

    # URL 编码 object_key
    import urllib.parse
    encoded_key = urllib.parse.quote(object_key, safe='')

    response = make_request(
        method="DELETE",
        endpoint=f"/files/{encoded_key}",
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print_json(result, "删除响应")
        print_success("文件删除成功")
        return True
    else:
        print_error(f"删除文件失败: {response.text}")
        return False

# ==================== 主函数 ====================

def main(no_cleanup=False):
    """主测试流程"""
    if no_cleanup:
        print_section("开始文件上传 API 测试（保留文件模式）")
    else:
        print_section("开始文件上传 API 测试")

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

    # 测试流程
    results = []
    temp_file = None

    try:
        # 1. 登录
        token = login()
        if not token:
            print_error("登录失败，无法继续测试")
            return
        results.append(("用户登录", True))

        # 2. 创建测试文件
        temp_file = create_test_file()
        results.append(("创建测试文件", True))

        # 3. 生成测试任务 ID
        task_id = str(uuid4())
        print_info(f"测试任务 ID: {task_id}")

        # 4. 上传文件
        success, upload_result = test_upload_file(token, task_id, temp_file)
        results.append(("上传文件到 OSS", success))

        if not success:
            print_error("文件上传失败，终止后续测试")
            return

        # 提取文件信息
        object_key = upload_result.get('object_key')
        filename = upload_result.get('filename', os.path.basename(temp_file))

        # 5. 获取下载 URL
        success, _ = test_get_download_url(token, task_id, filename)
        results.append(("获取下载 URL", success))

        # 6. 获取文件信息
        if object_key:
            success, _ = test_get_file_info(token, object_key)
            results.append(("获取文件信息", success))
        else:
            print_error("无法获取 object_key，跳过文件信息测试")
            results.append(("获取文件信息", False))

        # 7. 删除文件（清理）
        if no_cleanup:
            print_section("跳过文件删除（--no-cleanup 模式）")
            print_success(f"文件已保留在 OSS 上")
            print_info(f"Object Key: {object_key}")
            print_info(f"OSS URL: {upload_result.get('url')}")
            results.append(("保留文件在 OSS", True))
        else:
            if object_key:
                success = test_delete_file(token, object_key)
                results.append(("删除文件", success))
            else:
                print_error("无法删除文件，object_key 不存在")
                results.append(("删除文件", False))

    except Exception as e:
        print_error(f"测试过程发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # 清理本地临时文件
        if not no_cleanup:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    print_info(f"本地临时文件已清理: {temp_file}")
                except:
                    pass
        else:
            if temp_file and os.path.exists(temp_file):
                print_info(f"本地临时文件保留: {temp_file}")

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
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='OSS 文件上传测试')
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='保留上传的文件，不删除（用于在 OSS 控制台查看）'
    )
    args = parser.parse_args()

    main(no_cleanup=args.no_cleanup)
