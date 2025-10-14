"""
WebSocket服务 - 实时推送管理
"""
import json
from typing import Dict, List, Set, Optional, Any
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.logger import setup_logger

logger = setup_logger()


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        """初始化连接管理器"""
        # 用户ID -> WebSocket连接列表
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # WebSocket -> 用户ID映射
        self.connection_users: Dict[WebSocket, str] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        建立WebSocket连接

        Args:
            websocket: WebSocket连接对象
            user_id: 用户ID
        """
        await websocket.accept()

        # 添加到连接列表
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        self.connection_users[websocket] = user_id

        logger.info(f"User {user_id} connected. Total connections: {self.get_connection_count()}")

        # 发送连接成功消息
        await self.send_personal_message(
            user_id=user_id,
            message={
                "event": "connection:established",
                "data": {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    async def disconnect(self, websocket: WebSocket):
        """
        断开WebSocket连接

        Args:
            websocket: WebSocket连接对象
        """
        user_id = self.connection_users.get(websocket)

        if user_id and user_id in self.active_connections:
            # 移除连接
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            # 如果用户没有其他连接，清除用户记录
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        # 移除映射
        if websocket in self.connection_users:
            del self.connection_users[websocket]

        logger.info(f"User {user_id} disconnected. Total connections: {self.get_connection_count()}")

    async def send_personal_message(self, user_id: str, message: dict):
        """
        发送个人消息

        Args:
            user_id: 用户ID
            message: 消息字典
        """
        if user_id not in self.active_connections:
            logger.warning(f"User {user_id} not connected")
            return

        # 转换为JSON字符串
        message_json = json.dumps(message, ensure_ascii=False)

        # 发送给该用户的所有连接
        disconnected_sockets = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {str(e)}")
                disconnected_sockets.append(websocket)

        # 清理断开的连接
        for socket in disconnected_sockets:
            await self.disconnect(socket)

    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """
        广播消息给所有连接的用户

        Args:
            message: 消息字典
            exclude_user: 排除的用户ID（可选）
        """
        message_json = json.dumps(message, ensure_ascii=False)

        for user_id, connections in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue

            disconnected_sockets = []
            for websocket in connections:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.error(f"Failed to broadcast to user {user_id}: {str(e)}")
                    disconnected_sockets.append(websocket)

            # 清理断开的连接
            for socket in disconnected_sockets:
                await self.disconnect(socket)

    def get_connection_count(self) -> int:
        """
        获取当前连接总数

        Returns:
            连接总数
        """
        return sum(len(connections) for connections in self.active_connections.values())

    def get_user_count(self) -> int:
        """
        获取当前连接的用户数

        Returns:
            用户总数
        """
        return len(self.active_connections)

    def is_user_connected(self, user_id: str) -> bool:
        """
        检查用户是否在线

        Args:
            user_id: 用户ID

        Returns:
            是否在线
        """
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


class WebSocketService:
    """WebSocket服务类 - 业务消息推送"""

    def __init__(self, manager: ConnectionManager):
        """
        初始化WebSocket服务

        Args:
            manager: 连接管理器实例
        """
        self.manager = manager
        logger.info("WebSocketService initialized")

    async def send_task_progress(
        self,
        user_id: str,
        task_id: UUID,
        progress: int,
        current_frame: Optional[int] = None,
        total_frames: Optional[int] = None,
        message: Optional[str] = None
    ):
        """
        发送任务进度更新

        Args:
            user_id: 用户ID
            task_id: 任务ID
            progress: 进度百分比（0-100）
            current_frame: 当前帧
            total_frames: 总帧数
            message: 附加消息
        """
        data = {
            "task_id": str(task_id),
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }

        if current_frame is not None:
            data["current_frame"] = current_frame

        if total_frames is not None:
            data["total_frames"] = total_frames

        if message:
            data["message"] = message

        await self.manager.send_personal_message(
            user_id=user_id,
            message={
                "event": "task:progress",
                "data": data
            }
        )

        logger.debug(f"Task progress sent to user {user_id}: task={task_id}, progress={progress}%")

    async def send_task_status(
        self,
        user_id: str,
        task_id: UUID,
        status: str,
        message: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        发送任务状态更新

        Args:
            user_id: 用户ID
            task_id: 任务ID
            status: 任务状态
            message: 状态消息
            extra: 额外数据
        """
        data = {
            "task_id": str(task_id),
            "status": status,
            "timestamp": datetime.now().isoformat()
        }

        if message:
            data["message"] = message

        if extra:
            data.update(extra)

        await self.manager.send_personal_message(
            user_id=user_id,
            message={
                "event": "task:status",
                "data": data
            }
        )

        logger.info(f"Task status sent to user {user_id}: task={task_id}, status={status}")

    async def send_task_log(
        self,
        user_id: str,
        task_id: UUID,
        log_level: str,
        log_message: str
    ):
        """
        发送任务日志

        Args:
            user_id: 用户ID
            task_id: 任务ID
            log_level: 日志级别（info, warning, error）
            log_message: 日志消息
        """
        await self.manager.send_personal_message(
            user_id=user_id,
            message={
                "event": "task:log",
                "data": {
                    "task_id": str(task_id),
                    "level": log_level,
                    "message": log_message,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

        logger.debug(f"Task log sent to user {user_id}: task={task_id}, level={log_level}")

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        action_url: Optional[str] = None
    ):
        """
        发送通知消息

        Args:
            user_id: 用户ID
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型（info, success, warning, error）
            action_url: 操作链接
        """
        data = {
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.now().isoformat()
        }

        if action_url:
            data["action_url"] = action_url

        await self.manager.send_personal_message(
            user_id=user_id,
            message={
                "event": "notification",
                "data": data
            }
        )

        logger.info(f"Notification sent to user {user_id}: {title}")

    async def send_task_completed(
        self,
        user_id: str,
        task_id: UUID,
        result_files: List[str],
        render_time: float,
        cost: float
    ):
        """
        发送任务完成通知

        Args:
            user_id: 用户ID
            task_id: 任务ID
            result_files: 渲染结果文件列表
            render_time: 渲染时长（秒）
            cost: 渲染费用
        """
        await self.manager.send_personal_message(
            user_id=user_id,
            message={
                "event": "task:completed",
                "data": {
                    "task_id": str(task_id),
                    "result_files": result_files,
                    "render_time": render_time,
                    "cost": cost,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

        logger.info(f"Task completed notification sent to user {user_id}: task={task_id}")

    async def send_task_failed(
        self,
        user_id: str,
        task_id: UUID,
        error_message: str,
        error_details: Optional[str] = None
    ):
        """
        发送任务失败通知

        Args:
            user_id: 用户ID
            task_id: 任务ID
            error_message: 错误消息
            error_details: 错误详情
        """
        data = {
            "task_id": str(task_id),
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }

        if error_details:
            data["error_details"] = error_details

        await self.manager.send_personal_message(
            user_id=user_id,
            message={
                "event": "task:failed",
                "data": data
            }
        )

        logger.info(f"Task failed notification sent to user {user_id}: task={task_id}")


# 创建全局连接管理器和WebSocket服务实例
connection_manager = ConnectionManager()
websocket_service = WebSocketService(connection_manager)
