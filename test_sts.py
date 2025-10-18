#!/usr/bin/env python3
"""
STS 凭证获取测试脚本
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from app.services.sts_service import sts_service

def test_sts_credentials():
    """测试 STS 凭证获取"""
    print("=" * 60)
    print("🧪 测试 STS 凭证获取功能")
    print("=" * 60)

    try:
        # 获取临时凭证
        print("\n📝 参数:")
        print(f"  user_id: 1")
        print(f"  task_id: test_task_123")
        print(f"  duration: 3600 秒 (1小时)")

        print("\n⏳ 正在调用 STS API...")
        credentials = sts_service.get_upload_credentials(
            user_id=1,
            task_id="test_task_123",
            duration_seconds=3600
        )

        print("\n✅ STS 凭证获取成功!")
        print(f"\n📋 凭证信息:")
        print(f"  AccessKeyId: {credentials['accessKeyId'][:20]}...{credentials['accessKeyId'][-10:]}")
        print(f"  AccessKeySecret: {credentials['accessKeySecret'][:20]}...")
        print(f"  SecurityToken: {credentials['securityToken'][:50]}...")
        print(f"  到期时间: {credentials['expiration']}")

        print("\n✨ 测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sts_credentials()
    sys.exit(0 if success else 1)
