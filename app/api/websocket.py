"""
WebSocket API端点
"""
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from app.services.websocket_service import connection_manager, websocket_service
from app.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query(..., description="用户ID"),
    token: Optional[str] = Query(None, description="认证令牌（可选）")
):
    """
    WebSocket连接端点

    客户端连接示例：
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws?user_id=123&token=xxx');

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received:', message);

        // 处理不同类型的事件
        switch(message.event) {
            case 'task:progress':
                console.log('Task progress:', message.data);
                break;
            case 'task:status':
                console.log('Task status:', message.data);
                break;
            case 'notification':
                console.log('Notification:', message.data);
                break;
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };
    ```

    消息格式：
    ```json
    {
        "event": "task:progress",
        "data": {
            "task_id": "uuid",
            "progress": 50,
            "current_frame": 10,
            "total_frames": 20,
            "timestamp": "2024-01-01T12:00:00"
        }
    }
    ```

    支持的事件类型：
    - connection:established - 连接建立
    - task:progress - 任务进度更新
    - task:status - 任务状态更新
    - task:completed - 任务完成
    - task:failed - 任务失败
    - task:log - 任务日志
    - notification - 通知消息
    - ping - 心跳检测
    - pong - 心跳响应
    """
    try:
        # TODO: 在这里可以添加token验证逻辑
        # if token:
        #     # 验证token是否有效
        #     pass

        # 建立连接
        await connection_manager.connect(websocket, user_id)
        logger.info(f"WebSocket connection established for user: {user_id}")

        # 发送欢迎消息
        await websocket_service.send_notification(
            user_id=user_id,
            title="连接成功",
            message="WebSocket连接已建立，您将实时收到任务进度更新",
            notification_type="success"
        )

        # 保持连接并处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                message = json.loads(data)

                # 处理客户端消息
                await handle_client_message(websocket, user_id, message)

            except json.JSONDecodeError:
                # JSON解析错误
                await websocket.send_json({
                    "event": "error",
                    "data": {
                        "message": "Invalid JSON format"
                    }
                })
                logger.warning(f"Invalid JSON from user {user_id}: {data}")

            except WebSocketDisconnect:
                # 客户端主动断开连接
                raise

    except WebSocketDisconnect:
        # 断开连接
        await connection_manager.disconnect(websocket)
        logger.info(f"WebSocket connection closed for user: {user_id}")

    except Exception as e:
        # 其他错误
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
        finally:
            await connection_manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, user_id: str, message: dict):
    """
    处理客户端发送的消息

    Args:
        websocket: WebSocket连接
        user_id: 用户ID
        message: 客户端消息
    """
    try:
        event = message.get("event")
        data = message.get("data", {})

        if event == "ping":
            # 心跳检测
            await websocket.send_json({
                "event": "pong",
                "data": {
                    "timestamp": data.get("timestamp")
                }
            })
            logger.debug(f"Pong sent to user {user_id}")

        elif event == "subscribe":
            # 订阅特定任务的更新
            task_id = data.get("task_id")
            if task_id:
                logger.info(f"User {user_id} subscribed to task {task_id}")
                # TODO: 可以在这里实现订阅逻辑
                await websocket.send_json({
                    "event": "subscribed",
                    "data": {
                        "task_id": task_id,
                        "message": f"Subscribed to task {task_id}"
                    }
                })

        elif event == "unsubscribe":
            # 取消订阅
            task_id = data.get("task_id")
            if task_id:
                logger.info(f"User {user_id} unsubscribed from task {task_id}")
                # TODO: 可以在这里实现取消订阅逻辑
                await websocket.send_json({
                    "event": "unsubscribed",
                    "data": {
                        "task_id": task_id,
                        "message": f"Unsubscribed from task {task_id}"
                    }
                })

        else:
            # 未知事件类型
            logger.warning(f"Unknown event from user {user_id}: {event}")
            await websocket.send_json({
                "event": "error",
                "data": {
                    "message": f"Unknown event type: {event}"
                }
            })

    except Exception as e:
        logger.error(f"Error handling client message: {str(e)}")
        await websocket.send_json({
            "event": "error",
            "data": {
                "message": "Failed to process message"
            }
        })


@router.get("/stats", summary="获取WebSocket连接统计")
async def get_websocket_stats():
    """
    获取WebSocket连接统计信息

    返回当前在线用户数和连接总数
    """
    return {
        "total_connections": connection_manager.get_connection_count(),
        "total_users": connection_manager.get_user_count(),
        "active_users": list(connection_manager.active_connections.keys())
    }


@router.post("/send-notification", summary="发送通知（测试用）")
async def send_test_notification(
    user_id: str = Query(..., description="用户ID"),
    title: str = Query(..., description="通知标题"),
    message: str = Query(..., description="通知内容"),
    notification_type: str = Query("info", description="通知类型")
):
    """
    发送测试通知（仅用于开发测试）

    - **user_id**: 接收通知的用户ID
    - **title**: 通知标题
    - **message**: 通知内容
    - **notification_type**: 通知类型（info, success, warning, error）
    """
    if not connection_manager.is_user_connected(user_id):
        return {
            "success": False,
            "message": f"User {user_id} is not connected"
        }

    await websocket_service.send_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type
    )

    return {
        "success": True,
        "message": f"Notification sent to user {user_id}"
    }
