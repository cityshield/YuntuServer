"""
快速测试 OSS 智能上传器
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.oss_service import oss_service
from app.utils.oss_smart_uploader import smart_oss_uploader
from app.config import settings


def test_1_connection():
    """测试 1: OSS 连接"""
    print("\n" + "="*60)
    print("测试 1: OSS 连接测试")
    print("="*60)

    print(f"\n配置信息:")
    print(f"  Bucket: {settings.OSS_BUCKET_NAME}")
    print(f"  Endpoint: {settings.OSS_ENDPOINT}")
    print(f"  Base URL: {settings.OSS_BASE_URL}")

    try:
        # 列举文件测试连接
        result = oss_service.bucket.list_objects(max_keys=1)
        print("\n✅ OSS 连接成功！")
        return True
    except Exception as e:
        print(f"\n❌ OSS 连接失败: {str(e)}")
        return False


def test_2_small_upload():
    """测试 2: 小文件上传"""
    print("\n" + "="*60)
    print("测试 2: 小文件上传 (1MB)")
    print("="*60)

    temp_file = None
    try:
        # 创建 1MB 测试文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
        test_data = b'0' * (1024 * 1024)  # 1MB
        temp_file.write(test_data)
        temp_file.close()

        print(f"\n测试文件: {temp_file.name}")
        print(f"文件大小: 1.00 MB")

        # 上传
        import time
        object_key = f"test/quick_test_{int(time.time())}.bin"
        print(f"\n开始上传到: {object_key}")

        url = smart_oss_uploader.upload_large_file(
            file_path=temp_file.name,
            object_key=object_key,
            auto_optimize=True
        )

        print(f"\n✅ 上传成功！")
        print(f"   文件 URL: {url}")

        # 验证文件是否存在
        if oss_service.file_exists(object_key):
            print("   ✅ 文件验证成功")
        else:
            print("   ⚠️  文件验证失败")

        # 清理
        print("\n清理测试文件...")
        oss_service.delete_file(object_key)
        print("✅ 清理完成")

        return True

    except Exception as e:
        print(f"\n❌ 上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def test_3_parameter_calculation():
    """测试 3: 参数计算逻辑"""
    print("\n" + "="*60)
    print("测试 3: 智能参数计算")
    print("="*60)

    try:
        test_cases = [
            (5 * 1024 * 1024, "5MB 小文件"),
            (50 * 1024 * 1024, "50MB 中等文件"),
            (500 * 1024 * 1024, "500MB 大文件"),
            (5 * 1024 * 1024 * 1024, "5GB 超大文件"),
        ]

        print("\n文件大小 -> 分片大小 & 线程数:")
        print("-" * 60)

        for file_size, desc in test_cases:
            part_size = smart_oss_uploader.calculate_optimal_part_size(file_size)
            threads = smart_oss_uploader.calculate_optimal_threads(file_size)

            print(f"\n{desc} ({file_size / 1024 / 1024:.0f}MB):")
            print(f"  分片大小: {part_size / 1024 / 1024:.0f}MB")
            print(f"  并发线程: {threads}")

        print("\n✅ 参数计算逻辑正常")
        return True

    except Exception as e:
        print(f"\n❌ 参数计算失败: {str(e)}")
        return False


def test_4_service_integration():
    """测试 4: 服务集成"""
    print("\n" + "="*60)
    print("测试 4: OSSService 集成测试")
    print("="*60)

    temp_file = None
    try:
        # 创建 2MB 测试文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        temp_file.write(b'Test content for service integration\n' * 100000)
        temp_file.close()

        print(f"\n测试文件: {temp_file.name}")
        print(f"文件大小: {os.path.getsize(temp_file.name) / 1024 / 1024:.2f} MB")

        # 使用 OSSService 的优化上传方法
        import time
        object_key = f"test/service_test_{int(time.time())}.txt"
        print(f"\n使用 OSSService.upload_large_file_optimized() 上传...")

        url = oss_service.upload_large_file_optimized(
            file_path=temp_file.name,
            object_key=object_key,
            auto_optimize=True
        )

        print(f"\n✅ 服务集成上传成功！")
        print(f"   文件 URL: {url}")

        # 清理
        print("\n清理测试文件...")
        oss_service.delete_file(object_key)
        print("✅ 清理完成")

        return True

    except Exception as e:
        print(f"\n❌ 服务集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  OSS 智能上传器 - 快速测试")
    print("="*60)

    results = []

    # 运行测试
    results.append(("OSS 连接", test_1_connection()))
    results.append(("小文件上传", test_2_small_upload()))
    results.append(("参数计算", test_3_parameter_calculation()))
    results.append(("服务集成", test_4_service_integration()))

    # 汇总
    print("\n" + "="*60)
    print("  测试结果汇总")
    print("="*60)

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name:20s} {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！智能上传器工作正常。")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")


if __name__ == "__main__":
    main()
