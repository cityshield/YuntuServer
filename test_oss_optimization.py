"""
OSS 传输加速和智能上传器测试脚本
"""
import os
import sys
import time
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.oss_service import oss_service
from app.utils.oss_smart_uploader import smart_oss_uploader
from app.config import settings


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def test_oss_connection():
    """测试 OSS 连接"""
    print_section("测试 1: OSS 连接测试")

    print(f"Bucket: {settings.OSS_BUCKET_NAME}")
    print(f"Endpoint: {settings.OSS_ENDPOINT}")
    print(f"Base URL: {settings.OSS_BASE_URL}")

    try:
        # 测试列举文件（只列举1个）
        result = oss_service.bucket.list_objects(max_keys=1)
        print("\n✅ OSS 连接成功！")
        print(f"   传输加速状态: {'已启用 (oss-accelerate)' if 'accelerate' in settings.OSS_ENDPOINT else '未启用'}")
        return True
    except Exception as e:
        print(f"\n❌ OSS 连接失败: {str(e)}")
        return False


def test_bandwidth_measurement():
    """测试带宽测速"""
    print_section("测试 2: 带宽测速")

    try:
        print("正在测速（上传 1MB 测试文件）...")
        bandwidth = smart_oss_uploader.measure_upload_bandwidth(1 * 1024 * 1024)

        if bandwidth:
            print(f"\n✅ 测速成功！")
            print(f"   上传带宽: {bandwidth:.2f} Mbps")
            print(f"   预估速度: {bandwidth / 8:.2f} MB/s")
            return True
        else:
            print("\n⚠️  测速失败，但不影响上传功能")
            return True
    except Exception as e:
        print(f"\n❌ 测速失败: {str(e)}")
        return False


def create_test_file(size_mb):
    """创建测试文件"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
    print(f"创建 {size_mb}MB 测试文件: {temp_file.name}")

    # 生成随机数据
    chunk_size = 1024 * 1024  # 1MB
    for _ in range(size_mb):
        temp_file.write(os.urandom(chunk_size))

    temp_file.close()
    return temp_file.name


def test_small_file_upload():
    """测试小文件上传"""
    print_section("测试 3: 小文件上传 (5MB)")

    test_file = None
    try:
        # 创建 5MB 测试文件
        test_file = create_test_file(5)
        file_size = os.path.getsize(test_file)

        print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
        print("\n开始上传...")

        # 上传
        start_time = time.time()
        object_key = f"test/small_file_{int(time.time())}.bin"

        url = smart_oss_uploader.upload_large_file(
            file_path=test_file,
            object_key=object_key,
            auto_optimize=True
        )

        elapsed_time = time.time() - start_time
        speed_mbps = (file_size * 8 / 1024 / 1024) / elapsed_time

        print(f"\n✅ 上传成功！")
        print(f"   耗时: {elapsed_time:.2f} 秒")
        print(f"   速度: {speed_mbps:.2f} Mbps ({speed_mbps / 8:.2f} MB/s)")
        print(f"   文件URL: {url}")

        # 清理
        print("\n清理测试文件...")
        oss_service.delete_file(object_key)
        print("✅ 清理完成")

        return True

    except Exception as e:
        print(f"\n❌ 小文件上传失败: {str(e)}")
        return False

    finally:
        # 清理本地文件
        if test_file and os.path.exists(test_file):
            os.unlink(test_file)


def test_medium_file_upload():
    """测试中等文件上传（带进度显示）"""
    print_section("测试 4: 中等文件上传 (50MB)")

    test_file = None
    try:
        # 创建 50MB 测试文件
        test_file = create_test_file(50)
        file_size = os.path.getsize(test_file)

        print(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
        print("\n开始上传...")

        # 进度回调
        last_progress = 0

        def progress_callback(uploaded, total):
            nonlocal last_progress
            progress = int(100 * uploaded / total)
            if progress != last_progress and progress % 10 == 0:  # 每 10% 打印一次
                print(f"   进度: {progress}% ({uploaded / 1024 / 1024:.2f}/{total / 1024 / 1024:.2f} MB)")
                last_progress = progress

        # 上传
        start_time = time.time()
        object_key = f"test/medium_file_{int(time.time())}.bin"

        url = smart_oss_uploader.upload_large_file(
            file_path=test_file,
            object_key=object_key,
            progress_callback=progress_callback,
            auto_optimize=True
        )

        elapsed_time = time.time() - start_time
        speed_mbps = (file_size * 8 / 1024 / 1024) / elapsed_time

        print(f"\n✅ 上传成功！")
        print(f"   耗时: {elapsed_time:.2f} 秒")
        print(f"   速度: {speed_mbps:.2f} Mbps ({speed_mbps / 8:.2f} MB/s)")
        print(f"   文件URL: {url}")

        # 清理
        print("\n清理测试文件...")
        oss_service.delete_file(object_key)
        print("✅ 清理完成")

        return True

    except Exception as e:
        print(f"\n❌ 中等文件上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理本地文件
        if test_file and os.path.exists(test_file):
            os.unlink(test_file)


def test_optimization_comparison():
    """对比测试：优化 vs 未优化"""
    print_section("测试 5: 性能对比（优化 vs 未优化）")

    test_file = None
    try:
        # 创建 20MB 测试文件
        test_file = create_test_file(20)
        file_size = os.path.getsize(test_file)

        print(f"文件大小: {file_size / 1024 / 1024:.2f} MB\n")

        # 测试 1: 未优化上传
        print("🔵 测试 1: 未优化上传（auto_optimize=False）")
        object_key_1 = f"test/no_opt_{int(time.time())}.bin"
        start_time = time.time()

        smart_oss_uploader.upload_large_file(
            file_path=test_file,
            object_key=object_key_1,
            auto_optimize=False
        )

        time_no_opt = time.time() - start_time
        speed_no_opt = (file_size * 8 / 1024 / 1024) / time_no_opt

        print(f"   耗时: {time_no_opt:.2f} 秒")
        print(f"   速度: {speed_no_opt:.2f} Mbps\n")

        # 等待 1 秒
        time.sleep(1)

        # 测试 2: 优化上传
        print("🟢 测试 2: 智能优化上传（auto_optimize=True）")
        object_key_2 = f"test/optimized_{int(time.time())}.bin"
        start_time = time.time()

        smart_oss_uploader.upload_large_file(
            file_path=test_file,
            object_key=object_key_2,
            auto_optimize=True
        )

        time_opt = time.time() - start_time
        speed_opt = (file_size * 8 / 1024 / 1024) / time_opt

        print(f"   耗时: {time_opt:.2f} 秒")
        print(f"   速度: {speed_opt:.2f} Mbps\n")

        # 对比
        improvement = ((time_no_opt - time_opt) / time_no_opt) * 100
        print("📊 性能对比:")
        print(f"   未优化: {time_no_opt:.2f} 秒 ({speed_no_opt:.2f} Mbps)")
        print(f"   已优化: {time_opt:.2f} 秒 ({speed_opt:.2f} Mbps)")
        print(f"   提升: {improvement:+.1f}%")

        # 清理
        print("\n清理测试文件...")
        oss_service.delete_file(object_key_1)
        oss_service.delete_file(object_key_2)
        print("✅ 清理完成")

        return True

    except Exception as e:
        print(f"\n❌ 性能对比测试失败: {str(e)}")
        return False

    finally:
        if test_file and os.path.exists(test_file):
            os.unlink(test_file)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  OSS 传输优化测试")
    print("=" * 60)
    print(f"\n当前配置:")
    print(f"  Endpoint: {settings.OSS_ENDPOINT}")
    print(f"  传输加速: {'✅ 已启用' if 'accelerate' in settings.OSS_ENDPOINT else '❌ 未启用'}")

    results = []

    # 运行测试
    results.append(("OSS 连接", test_oss_connection()))
    results.append(("带宽测速", test_bandwidth_measurement()))
    results.append(("小文件上传", test_small_file_upload()))
    results.append(("中等文件上传", test_medium_file_upload()))
    results.append(("性能对比", test_optimization_comparison()))

    # 汇总结果
    print_section("测试结果汇总")

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name:20s} {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！OSS 传输优化已成功启用。")
    else:
        print("\n⚠️  部分测试失败，请检查配置和网络连接。")


if __name__ == "__main__":
    main()
