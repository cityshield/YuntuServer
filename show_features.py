"""
展示OSS和WebSocket功能
"""
import json
from uuid import uuid4
from datetime import datetime


def show_created_files():
    """显示创建的文件"""
    print("\n" + "="*80)
    print(" "*25 + "创建的文件列表")
    print("="*80)

    files = [
        {
            "path": "/app/services/oss_service.py",
            "size": "5.6 KB",
            "description": "阿里云OSS服务核心类"
        },
        {
            "path": "/app/services/file_service.py",
            "size": "7.0 KB",
            "description": "文件管理服务层"
        },
        {
            "path": "/app/services/websocket_service.py",
            "size": "11.5 KB",
            "description": "WebSocket连接管理和消息推送服务"
        },
        {
            "path": "/app/api/v1/files.py",
            "size": "7.5 KB",
            "description": "文件管理API端点"
        },
        {
            "path": "/app/api/websocket.py",
            "size": "7.8 KB",
            "description": "WebSocket API端点"
        }
    ]

    for i, file in enumerate(files, 1):
        print(f"\n{i}. {file['path']}")
        print(f"   大小: {file['size']}")
        print(f"   描述: {file['description']}")


def show_oss_features():
    """显示OSS功能"""
    print("\n" + "="*80)
    print(" "*25 + "OSS 核心功能")
    print("="*80)

    features = [
        {
            "name": "upload_file()",
            "description": "上传文件到OSS",
            "params": "file_content, object_key, content_type",
            "returns": "文件访问URL"
        },
        {
            "name": "generate_upload_url()",
            "description": "生成预签名上传URL",
            "params": "object_key, expire_time, content_type",
            "returns": "预签名上传URL（用于客户端直接上传）"
        },
        {
            "name": "generate_download_url()",
            "description": "生成预签名下载URL",
            "params": "object_key, expire_time, filename",
            "returns": "预签名下载URL（可自定义下载文件名）"
        },
        {
            "name": "delete_file()",
            "description": "删除OSS文件",
            "params": "object_key",
            "returns": "是否删除成功"
        },
        {
            "name": "file_exists()",
            "description": "检查文件是否存在",
            "params": "object_key",
            "returns": "布尔值"
        },
        {
            "name": "get_file_info()",
            "description": "获取文件元数据",
            "params": "object_key",
            "returns": "文件大小、类型、修改时间等信息"
        }
    ]

    for i, feature in enumerate(features, 1):
        print(f"\n{i}. {feature['name']}")
        print(f"   功能: {feature['description']}")
        print(f"   参数: {feature['params']}")
        print(f"   返回: {feature['returns']}")

    print("\n\n文件服务层功能:")
    file_service_features = [
        "upload_scene_file() - 上传场景文件（自动生成路径）",
        "upload_result_file() - 上传渲染结果文件",
        "get_download_url() - 获取下载链接（自动检查文件存在）",
        "get_upload_url() - 获取客户端直接上传URL",
        "delete_file() - 删除文件",
        "get_file_info() - 获取文件详细信息"
    ]

    for i, feature in enumerate(file_service_features, 1):
        print(f"  {i}. {feature}")


def show_websocket_features():
    """显示WebSocket功能"""
    print("\n" + "="*80)
    print(" "*25 + "WebSocket 核心功能")
    print("="*80)

    print("\n连接管理器 (ConnectionManager):")
    connection_features = [
        {
            "name": "connect()",
            "description": "建立WebSocket连接，支持单用户多连接"
        },
        {
            "name": "disconnect()",
            "description": "断开连接并自动清理资源"
        },
        {
            "name": "send_personal_message()",
            "description": "发送个人消息到用户的所有连接"
        },
        {
            "name": "broadcast()",
            "description": "广播消息给所有在线用户"
        },
        {
            "name": "get_connection_count()",
            "description": "获取当前连接总数"
        },
        {
            "name": "get_user_count()",
            "description": "获取在线用户数"
        },
        {
            "name": "is_user_connected()",
            "description": "检查用户是否在线"
        }
    ]

    for i, feature in enumerate(connection_features, 1):
        print(f"  {i}. {feature['name']:<30} - {feature['description']}")

    print("\n\nWebSocket服务 (WebSocketService):")
    ws_features = [
        {
            "name": "send_task_progress()",
            "description": "发送任务进度更新（进度百分比、当前帧、总帧数）"
        },
        {
            "name": "send_task_status()",
            "description": "发送任务状态更新（pending, running, completed, failed）"
        },
        {
            "name": "send_task_log()",
            "description": "发送任务日志（info, warning, error）"
        },
        {
            "name": "send_notification()",
            "description": "发送通知消息（info, success, warning, error）"
        },
        {
            "name": "send_task_completed()",
            "description": "发送任务完成通知（包含结果文件、时长、费用）"
        },
        {
            "name": "send_task_failed()",
            "description": "发送任务失败通知（包含错误信息）"
        }
    ]

    for i, feature in enumerate(ws_features, 1):
        print(f"  {i}. {feature['name']:<30} - {feature['description']}")


def show_message_examples():
    """显示消息格式示例"""
    print("\n" + "="*80)
    print(" "*25 + "WebSocket 消息格式示例")
    print("="*80)

    examples = [
        {
            "title": "任务进度消息",
            "message": {
                "event": "task:progress",
                "data": {
                    "task_id": str(uuid4()),
                    "progress": 50,
                    "current_frame": 10,
                    "total_frames": 20,
                    "message": "正在渲染第10帧",
                    "timestamp": "2024-01-01T12:00:00"
                }
            }
        },
        {
            "title": "任务状态消息",
            "message": {
                "event": "task:status",
                "data": {
                    "task_id": str(uuid4()),
                    "status": "rendering",
                    "message": "任务正在渲染中",
                    "timestamp": "2024-01-01T12:00:00"
                }
            }
        },
        {
            "title": "任务完成消息",
            "message": {
                "event": "task:completed",
                "data": {
                    "task_id": str(uuid4()),
                    "result_files": ["frame_001.png", "frame_002.png"],
                    "render_time": 120.5,
                    "cost": 60.25,
                    "timestamp": "2024-01-01T12:00:00"
                }
            }
        },
        {
            "title": "通知消息",
            "message": {
                "event": "notification",
                "data": {
                    "title": "系统通知",
                    "message": "您的账户余额不足",
                    "type": "warning",
                    "action_url": "/billing/recharge",
                    "timestamp": "2024-01-01T12:00:00"
                }
            }
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print(json.dumps(example['message'], indent=2, ensure_ascii=False))


def show_api_endpoints():
    """显示API端点"""
    print("\n" + "="*80)
    print(" "*30 + "API 端点")
    print("="*80)

    print("\n文件管理 API (/api/v1/files):")
    file_apis = [
        {
            "method": "POST",
            "path": "/upload",
            "description": "上传场景文件",
            "example": "POST /api/v1/files/upload?task_id=uuid"
        },
        {
            "method": "GET",
            "path": "/download/{task_id}/{filename}",
            "description": "生成下载URL",
            "example": "GET /api/v1/files/download/uuid/scene.ma?expire_time=3600"
        },
        {
            "method": "POST",
            "path": "/upload-url",
            "description": "获取预签名上传URL",
            "example": "POST /api/v1/files/upload-url?task_id=uuid&filename=scene.ma"
        },
        {
            "method": "GET",
            "path": "/info/{object_key}",
            "description": "获取文件信息",
            "example": "GET /api/v1/files/info/scenes/20240101/uuid/scene.ma"
        },
        {
            "method": "DELETE",
            "path": "/{object_key}",
            "description": "删除文件",
            "example": "DELETE /api/v1/files/scenes/20240101/uuid/scene.ma"
        }
    ]

    for i, api in enumerate(file_apis, 1):
        print(f"\n  {i}. {api['method']:<8} {api['path']}")
        print(f"     描述: {api['description']}")
        print(f"     示例: {api['example']}")

    print("\n\nWebSocket API:")
    ws_apis = [
        {
            "method": "WebSocket",
            "path": "/ws",
            "description": "建立WebSocket连接",
            "example": "ws://localhost:8000/ws?user_id=123&token=xxx"
        },
        {
            "method": "GET",
            "path": "/stats",
            "description": "获取连接统计",
            "example": "GET /stats"
        },
        {
            "method": "POST",
            "path": "/send-notification",
            "description": "发送测试通知",
            "example": "POST /send-notification?user_id=123&title=测试&message=消息"
        }
    ]

    for i, api in enumerate(ws_apis, 1):
        print(f"\n  {i}. {api['method']:<12} {api['path']}")
        print(f"     描述: {api['description']}")
        print(f"     示例: {api['example']}")


def show_integration_example():
    """显示集成示例"""
    print("\n" + "="*80)
    print(" "*30 + "集成示例")
    print("="*80)

    print("""
在渲染任务中使用OSS和WebSocket（伪代码）:

async def process_render_task(task_id: UUID, user_id: str):
    # 1. 发送任务开始状态
    await websocket_service.send_task_status(
        user_id=user_id,
        task_id=task_id,
        status="starting",
        message="正在初始化渲染任务"
    )

    # 2. 从OSS下载场景文件
    scene_url = file_service.get_download_url(
        object_key=f"scenes/20240101/{task_id}/scene.ma"
    )
    scene_data = await download_file(scene_url)

    # 3. 发送渲染中状态
    await websocket_service.send_task_status(
        user_id=user_id,
        task_id=task_id,
        status="rendering",
        message="正在渲染"
    )

    # 4. 渲染循环 - 实时推送进度
    for frame in range(1, total_frames + 1):
        # 计算进度
        progress = int((frame / total_frames) * 100)

        # 推送进度更新
        await websocket_service.send_task_progress(
            user_id=user_id,
            task_id=task_id,
            progress=progress,
            current_frame=frame,
            total_frames=total_frames,
            message=f"正在渲染第{frame}帧"
        )

        # 渲染当前帧
        frame_data = await render_frame(frame)

        # 上传渲染结果到OSS
        await file_service.upload_result_file(
            task_id=task_id,
            filename=f"frame_{frame:04d}.png",
            file_content=frame_data,
            content_type="image/png"
        )

    # 5. 发送任务完成通知
    await websocket_service.send_task_completed(
        user_id=user_id,
        task_id=task_id,
        result_files=[f"frame_{i:04d}.png" for i in range(1, total_frames + 1)],
        render_time=120.5,
        cost=60.25
    )

    # 6. 发送系统通知
    await websocket_service.send_notification(
        user_id=user_id,
        title="渲染完成",
        message=f"任务 {task_id} 已完成渲染，共 {total_frames} 帧",
        notification_type="success",
        action_url=f"/tasks/{task_id}/results"
    )
    """)


def show_config():
    """显示配置要求"""
    print("\n" + "="*80)
    print(" "*30 + "配置要求")
    print("="*80)

    print("\n在 .env 文件中配置以下环境变量:\n")

    configs = [
        ("OSS_ACCESS_KEY_ID", "阿里云OSS访问密钥ID"),
        ("OSS_ACCESS_KEY_SECRET", "阿里云OSS访问密钥Secret"),
        ("OSS_BUCKET_NAME", "OSS存储桶名称"),
        ("OSS_ENDPOINT", "OSS区域端点（如: oss-cn-beijing.aliyuncs.com）"),
        ("OSS_BASE_URL", "OSS访问URL"),
        ("OSS_SCENE_FOLDER", "场景文件存储目录（默认: scenes）"),
        ("OSS_RESULT_FOLDER", "渲染结果存储目录（默认: results）")
    ]

    for key, desc in configs:
        print(f"  {key:<25} - {desc}")


def main():
    """主函数"""
    print("\n" + "="*80)
    print(" "*15 + "YuntuServer - OSS & WebSocket 功能总览")
    print("="*80)

    show_created_files()
    show_oss_features()
    show_websocket_features()
    show_message_examples()
    show_api_endpoints()
    show_integration_example()
    show_config()

    print("\n" + "="*80)
    print(" "*32 + "总结")
    print("="*80)
    print("""
已成功创建5个文件，实现了完整的OSS文件上传下载和WebSocket实时推送功能：

OSS功能:
  ✓ 文件上传到阿里云OSS
  ✓ 生成预签名上传/下载URL（客户端直接上传/下载）
  ✓ 文件管理（删除、查询、检查存在）
  ✓ 场景文件和渲染结果分类存储
  ✓ 自动生成带日期和任务ID的文件路径

WebSocket功能:
  ✓ 实时任务进度推送
  ✓ 任务状态变更通知
  ✓ 任务日志实时输出
  ✓ 系统通知推送
  ✓ 连接管理和心跳检测
  ✓ 支持单用户多连接
  ✓ 个人消息和广播消息

下一步:
  1. 在 .env 文件中配置OSS参数
  2. 安装依赖: pip install oss2 websockets
  3. 启动服务: uvicorn app.main:app --reload
  4. 访问文档: http://localhost:8000/docs
  5. 查看详细使用说明: OSS_WEBSOCKET_USAGE.md

    """)
    print("="*80)
    print()


if __name__ == "__main__":
    main()
