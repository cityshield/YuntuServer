"""
OSS和WebSocket功能测试脚本
"""
import asyncio
import json
from uuid import uuid4
from datetime import datetime

# 模拟测试，不需要实际连接


def test_oss_service():
    """测试OSS服务"""
    print("\n" + "="*60)
    print("测试 OSS 服务")
    print("="*60)

    from app.services.oss_service import OSSService

    # 展示OSS服务的功能
    print("\n可用功能：")
    print("1. upload_file(file_content, object_key, content_type)")
    print("   - 上传文件到OSS")
    print("   - 返回文件访问URL")

    print("\n2. generate_upload_url(object_key, expire_time, content_type)")
    print("   - 生成预签名上传URL")
    print("   - 用于客户端直接上传")

    print("\n3. generate_download_url(object_key, expire_time, filename)")
    print("   - 生成预签名下载URL")
    print("   - 支持自定义下载文件名")

    print("\n4. delete_file(object_key)")
    print("   - 删除OSS文件")

    print("\n5. file_exists(object_key)")
    print("   - 检查文件是否存在")

    print("\n6. get_file_info(object_key)")
    print("   - 获取文件元数据信息")

    print("\n配置要求：")
    print("  - OSS_ACCESS_KEY_ID")
    print("  - OSS_ACCESS_KEY_SECRET")
    print("  - OSS_BUCKET_NAME")
    print("  - OSS_ENDPOINT")
    print("  - OSS_BASE_URL")


def test_file_service():
    """测试文件服务"""
    print("\n" + "="*60)
    print("测试文件管理服务")
    print("="*60)

    from app.services.file_service import FileService

    print("\n可用功能：")
    print("1. upload_scene_file(task_id, filename, file_content, content_type)")
    print("   - 上传场景文件")
    print("   - 自动生成带日期和任务ID的路径")
    print("   - 路径格式: scenes/YYYYMMDD/task_id/filename")

    print("\n2. upload_result_file(task_id, filename, file_content, content_type)")
    print("   - 上传渲染结果文件")
    print("   - 路径格式: results/YYYYMMDD/task_id/filename")

    print("\n3. get_download_url(object_key, filename, expire_time)")
    print("   - 获取文件下载URL")
    print("   - 自动检查文件是否存在")

    print("\n4. get_upload_url(task_id, filename, content_type, expire_time)")
    print("   - 获取客户端直接上传URL")

    print("\n5. delete_file(object_key)")
    print("   - 删除文件")

    print("\n6. get_file_info(object_key)")
    print("   - 获取文件详细信息")


async def test_websocket_service():
    """测试WebSocket服务"""
    print("\n" + "="*60)
    print("测试 WebSocket 服务")
    print("="*60)

    from app.services.websocket_service import ConnectionManager, WebSocketService

    print("\n连接管理器功能：")
    print("1. connect(websocket, user_id)")
    print("   - 建立WebSocket连接")
    print("   - 支持单用户多连接")

    print("\n2. disconnect(websocket)")
    print("   - 断开连接")
    print("   - 自动清理资源")

    print("\n3. send_personal_message(user_id, message)")
    print("   - 发送个人消息")
    print("   - 发送给用户的所有连接")

    print("\n4. broadcast(message, exclude_user)")
    print("   - 广播消息给所有用户")
    print("   - 可排除特定用户")

    print("\n5. get_connection_count()")
    print("   - 获取当前连接总数")

    print("\n6. get_user_count()")
    print("   - 获取在线用户数")

    print("\n7. is_user_connected(user_id)")
    print("   - 检查用户是否在线")

    print("\n\nWebSocket服务功能：")
    print("1. send_task_progress(user_id, task_id, progress, ...)")
    print("   - 发送任务进度更新")
    print("   - 包含进度百分比、当前帧、总帧数等")

    print("\n2. send_task_status(user_id, task_id, status, message)")
    print("   - 发送任务状态更新")
    print("   - 状态包括：pending, running, completed, failed等")

    print("\n3. send_task_log(user_id, task_id, log_level, log_message)")
    print("   - 发送任务日志")
    print("   - 日志级别：info, warning, error")

    print("\n4. send_notification(user_id, title, message, type)")
    print("   - 发送通知消息")
    print("   - 类型：info, success, warning, error")

    print("\n5. send_task_completed(user_id, task_id, result_files, ...)")
    print("   - 发送任务完成通知")
    print("   - 包含结果文件、渲染时长、费用等")

    print("\n6. send_task_failed(user_id, task_id, error_message)")
    print("   - 发送任务失败通知")


def test_websocket_message_format():
    """测试WebSocket消息格式"""
    print("\n" + "="*60)
    print("WebSocket 消息格式示例")
    print("="*60)

    # 任务进度消息
    progress_msg = {
        "event": "task:progress",
        "data": {
            "task_id": str(uuid4()),
            "progress": 50,
            "current_frame": 10,
            "total_frames": 20,
            "message": "正在渲染第10帧",
            "timestamp": datetime.now().isoformat()
        }
    }
    print("\n1. 任务进度消息：")
    print(json.dumps(progress_msg, indent=2, ensure_ascii=False))

    # 任务状态消息
    status_msg = {
        "event": "task:status",
        "data": {
            "task_id": str(uuid4()),
            "status": "rendering",
            "message": "任务正在渲染中",
            "timestamp": datetime.now().isoformat()
        }
    }
    print("\n2. 任务状态消息：")
    print(json.dumps(status_msg, indent=2, ensure_ascii=False))

    # 任务完成消息
    completed_msg = {
        "event": "task:completed",
        "data": {
            "task_id": str(uuid4()),
            "result_files": ["frame_001.png", "frame_002.png"],
            "render_time": 120.5,
            "cost": 60.25,
            "timestamp": datetime.now().isoformat()
        }
    }
    print("\n3. 任务完成消息：")
    print(json.dumps(completed_msg, indent=2, ensure_ascii=False))

    # 通知消息
    notification_msg = {
        "event": "notification",
        "data": {
            "title": "系统通知",
            "message": "您的账户余额不足",
            "type": "warning",
            "action_url": "/billing/recharge",
            "timestamp": datetime.now().isoformat()
        }
    }
    print("\n4. 通知消息：")
    print(json.dumps(notification_msg, indent=2, ensure_ascii=False))

    # 心跳消息
    ping_msg = {
        "event": "ping",
        "data": {
            "timestamp": datetime.now().isoformat()
        }
    }
    print("\n5. 心跳消息（客户端发送）：")
    print(json.dumps(ping_msg, indent=2, ensure_ascii=False))

    pong_msg = {
        "event": "pong",
        "data": {
            "timestamp": datetime.now().isoformat()
        }
    }
    print("\n6. 心跳响应（服务端返回）：")
    print(json.dumps(pong_msg, indent=2, ensure_ascii=False))


def test_api_endpoints():
    """测试API端点"""
    print("\n" + "="*60)
    print("API 端点测试示例")
    print("="*60)

    print("\n文件API：")
    print("\n1. 上传文件:")
    print("   POST /api/v1/files/upload?task_id=uuid")
    print("   Content-Type: multipart/form-data")
    print("   Body: file=@scene.ma")

    print("\n2. 生成下载URL:")
    print("   GET /api/v1/files/download/{task_id}/{filename}?expire_time=3600")

    print("\n3. 获取上传URL:")
    print("   POST /api/v1/files/upload-url?task_id=uuid&filename=scene.ma")

    print("\n4. 获取文件信息:")
    print("   GET /api/v1/files/info/{object_key}")

    print("\n5. 删除文件:")
    print("   DELETE /api/v1/files/{object_key}")

    print("\n\nWebSocket API：")
    print("\n1. 建立连接:")
    print("   WebSocket: ws://localhost:8000/ws?user_id=123&token=xxx")

    print("\n2. 获取连接统计:")
    print("   GET /stats")

    print("\n3. 发送测试通知:")
    print("   POST /send-notification?user_id=123&title=测试&message=消息")


def print_integration_example():
    """打印集成示例"""
    print("\n" + "="*60)
    print("集成示例")
    print("="*60)

    print("\n在渲染任务中使用（伪代码）：")
    print("""
async def process_render_task(task_id: UUID, user_id: str):
    # 1. 发送任务开始状态
    await websocket_service.send_task_status(
        user_id=user_id,
        task_id=task_id,
        status="starting",
        message="正在初始化渲染任务"
    )

    # 2. 下载场景文件
    scene_file = await file_service.get_download_url(
        object_key=f"scenes/20240101/{task_id}/scene.ma"
    )

    # 3. 开始渲染
    await websocket_service.send_task_status(
        user_id=user_id,
        task_id=task_id,
        status="rendering",
        message="正在渲染"
    )

    # 4. 渲染进度更新
    for frame in range(1, total_frames + 1):
        progress = int((frame / total_frames) * 100)

        await websocket_service.send_task_progress(
            user_id=user_id,
            task_id=task_id,
            progress=progress,
            current_frame=frame,
            total_frames=total_frames
        )

        # 渲染当前帧...
        await render_frame(frame)

    # 5. 上传渲染结果
    for frame_file in result_files:
        await file_service.upload_result_file(
            task_id=task_id,
            filename=frame_file.name,
            file_content=frame_file.content
        )

    # 6. 发送任务完成通知
    await websocket_service.send_task_completed(
        user_id=user_id,
        task_id=task_id,
        result_files=result_file_urls,
        render_time=120.5,
        cost=60.25
    )

    # 7. 发送通知
    await websocket_service.send_notification(
        user_id=user_id,
        title="渲染完成",
        message=f"任务 {task_id} 已完成渲染",
        notification_type="success",
        action_url=f"/tasks/{task_id}"
    )
    """)


def main():
    """主函数"""
    print("\n" + "="*80)
    print(" "*20 + "YuntuServer - OSS & WebSocket 功能测试")
    print("="*80)

    test_oss_service()
    test_file_service()

    # WebSocket测试需要异步运行
    asyncio.run(test_websocket_service())

    test_websocket_message_format()
    test_api_endpoints()
    print_integration_example()

    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)
    print("\n提示：")
    print("1. 确保.env文件中配置了正确的OSS参数")
    print("2. 确保安装了oss2库: pip install oss2")
    print("3. 确保安装了websockets库: pip install websockets")
    print("4. 使用 'python test_websocket_oss.py' 运行此测试")
    print("5. 查看 OSS_WEBSOCKET_USAGE.md 获取详细使用说明")
    print()


if __name__ == "__main__":
    main()
