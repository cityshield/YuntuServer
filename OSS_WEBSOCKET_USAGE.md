# OSS文件上传下载和WebSocket实时推送使用说明

## 创建的文件

### 1. 服务层文件

#### `/app/services/oss_service.py`
阿里云OSS服务核心类，提供以下功能：
- `upload_file()` - 上传文件到OSS
- `generate_upload_url()` - 生成预签名上传URL
- `generate_download_url()` - 生成预签名下载URL
- `delete_file()` - 删除OSS文件
- `file_exists()` - 检查文件是否存在
- `get_file_info()` - 获取文件元数据信息

#### `/app/services/file_service.py`
文件管理服务层，整合OSS服务，提供业务层功能：
- `upload_scene_file()` - 上传场景文件
- `upload_result_file()` - 上传渲染结果文件
- `get_download_url()` - 获取下载链接
- `get_upload_url()` - 获取上传URL（用于客户端直接上传）
- `delete_file()` - 删除文件
- `get_file_info()` - 获取文件信息

#### `/app/services/websocket_service.py`
WebSocket管理服务，包含两个主要类：

**ConnectionManager类** - 连接管理
- `connect()` - 建立WebSocket连接
- `disconnect()` - 断开连接
- `send_personal_message()` - 发送个人消息
- `broadcast()` - 广播消息给所有用户
- `get_connection_count()` - 获取连接总数
- `get_user_count()` - 获取在线用户数
- `is_user_connected()` - 检查用户是否在线

**WebSocketService类** - 业务消息推送
- `send_task_progress()` - 发送任务进度更新
- `send_task_status()` - 发送任务状态更新
- `send_task_log()` - 发送任务日志
- `send_notification()` - 发送通知消息
- `send_task_completed()` - 发送任务完成通知
- `send_task_failed()` - 发送任务失败通知

### 2. API端点文件

#### `/app/api/v1/files.py`
文件管理API端点，提供以下接口：
- `POST /api/v1/files/upload` - 上传场景文件
- `GET /api/v1/files/download/{task_id}/{filename}` - 生成下载URL
- `POST /api/v1/files/upload-url` - 获取预签名上传URL
- `GET /api/v1/files/info/{object_key}` - 获取文件信息
- `DELETE /api/v1/files/{object_key}` - 删除文件

#### `/app/api/websocket.py`
WebSocket API端点：
- `GET /ws` - WebSocket连接端点
- `GET /stats` - 获取连接统计
- `POST /send-notification` - 发送测试通知

## OSS配置

在`.env`文件中配置以下环境变量：

```bash
# 阿里云OSS配置
OSS_ACCESS_KEY_ID=your_access_key_id          # OSS访问密钥ID
OSS_ACCESS_KEY_SECRET=your_access_key_secret  # OSS访问密钥Secret
OSS_BUCKET_NAME=yuntu-bucket                  # OSS存储桶名称
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com      # OSS区域端点
OSS_BASE_URL=https://yuntu-bucket.oss-cn-beijing.aliyuncs.com  # OSS访问URL
OSS_SCENE_FOLDER=scenes                       # 场景文件存储目录
OSS_RESULT_FOLDER=results                     # 渲染结果存储目录
```

## 使用示例

### 1. 文件上传（服务端上传）

```python
from app.services.file_service import file_service
from uuid import UUID

# 上传场景文件
result = await file_service.upload_scene_file(
    task_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    filename="scene.ma",
    file_content=file_bytes,
    content_type="application/octet-stream"
)

# 返回结果
# {
#     "filename": "scene.ma",
#     "object_key": "scenes/20240101/task_id/scene.ma",
#     "url": "https://bucket.oss.com/scenes/20240101/task_id/scene.ma",
#     "size": 1024000,
#     "content_type": "application/octet-stream",
#     "uploaded_at": "2024-01-01T12:00:00"
# }
```

### 2. 文件上传（客户端直接上传）

```python
# 后端生成上传URL
result = file_service.get_upload_url(
    task_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    filename="scene.ma",
    content_type="application/octet-stream",
    expire_time=3600  # 1小时过期
)

# 客户端使用返回的upload_url进行PUT上传
# PUT result["upload_url"]
# Content-Type: application/octet-stream
# Body: file binary data
```

### 3. 文件下载

```python
# 生成下载URL
download_url = file_service.get_download_url(
    object_key="scenes/20240101/task_id/scene.ma",
    filename="scene.ma",  # 下载时的文件名
    expire_time=3600  # 1小时过期
)

# 客户端可以直接通过这个URL下载文件
```

### 4. WebSocket连接（前端）

```javascript
// 建立WebSocket连接
const ws = new WebSocket('ws://localhost:8000/ws?user_id=123&token=xxx');

// 连接成功
ws.onopen = () => {
    console.log('WebSocket connected');

    // 发送心跳
    setInterval(() => {
        ws.send(JSON.stringify({
            event: 'ping',
            data: { timestamp: Date.now() }
        }));
    }, 30000);
};

// 接收消息
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received:', message);

    // 处理不同类型的事件
    switch(message.event) {
        case 'connection:established':
            console.log('Connection established:', message.data);
            break;

        case 'task:progress':
            // 任务进度更新
            console.log('Progress:', message.data.progress + '%');
            updateProgressBar(message.data.task_id, message.data.progress);
            break;

        case 'task:status':
            // 任务状态更新
            console.log('Status:', message.data.status);
            updateTaskStatus(message.data.task_id, message.data.status);
            break;

        case 'task:completed':
            // 任务完成
            console.log('Task completed:', message.data);
            showNotification('任务完成', '渲染任务已完成');
            break;

        case 'task:failed':
            // 任务失败
            console.error('Task failed:', message.data.error_message);
            showError(message.data.error_message);
            break;

        case 'notification':
            // 通知消息
            showNotification(message.data.title, message.data.message);
            break;

        case 'pong':
            // 心跳响应
            console.log('Pong received');
            break;
    }
};

// 错误处理
ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

// 连接关闭
ws.onclose = () => {
    console.log('WebSocket disconnected');
    // 可以实现重连逻辑
};

// 订阅特定任务
ws.send(JSON.stringify({
    event: 'subscribe',
    data: { task_id: 'task-uuid' }
}));
```

### 5. WebSocket推送（后端）

```python
from app.services.websocket_service import websocket_service
from uuid import UUID

# 发送任务进度
await websocket_service.send_task_progress(
    user_id="user123",
    task_id=UUID("task-uuid"),
    progress=50,
    current_frame=10,
    total_frames=20,
    message="正在渲染第10帧"
)

# 发送任务状态
await websocket_service.send_task_status(
    user_id="user123",
    task_id=UUID("task-uuid"),
    status="rendering",
    message="任务正在渲染中"
)

# 发送任务完成通知
await websocket_service.send_task_completed(
    user_id="user123",
    task_id=UUID("task-uuid"),
    result_files=["frame_001.png", "frame_002.png"],
    render_time=120.5,
    cost=60.25
)

# 发送任务失败通知
await websocket_service.send_task_failed(
    user_id="user123",
    task_id=UUID("task-uuid"),
    error_message="渲染失败：内存不足",
    error_details="详细错误信息..."
)

# 发送通知
await websocket_service.send_notification(
    user_id="user123",
    title="系统通知",
    message="您的账户余额不足",
    notification_type="warning",
    action_url="/billing/recharge"
)
```

## WebSocket消息格式

所有WebSocket消息都使用统一的JSON格式：

```json
{
    "event": "事件类型",
    "data": {
        "具体数据字段"
    }
}
```

### 支持的事件类型

#### 服务端推送事件

| 事件类型 | 说明 | 数据字段 |
|---------|------|---------|
| `connection:established` | 连接建立 | `user_id`, `timestamp` |
| `task:progress` | 任务进度 | `task_id`, `progress`, `current_frame`, `total_frames`, `message` |
| `task:status` | 任务状态 | `task_id`, `status`, `message` |
| `task:completed` | 任务完成 | `task_id`, `result_files`, `render_time`, `cost` |
| `task:failed` | 任务失败 | `task_id`, `error_message`, `error_details` |
| `task:log` | 任务日志 | `task_id`, `level`, `message` |
| `notification` | 通知消息 | `title`, `message`, `type`, `action_url` |
| `pong` | 心跳响应 | `timestamp` |

#### 客户端发送事件

| 事件类型 | 说明 | 数据字段 |
|---------|------|---------|
| `ping` | 心跳检测 | `timestamp` |
| `subscribe` | 订阅任务 | `task_id` |
| `unsubscribe` | 取消订阅 | `task_id` |

## API端点说明

### 文件API

#### 1. 上传文件
```bash
POST /api/v1/files/upload?task_id=uuid
Content-Type: multipart/form-data

# 响应
{
    "filename": "scene.ma",
    "object_key": "scenes/20240101/uuid/scene.ma",
    "url": "https://...",
    "size": 1024000,
    "content_type": "application/octet-stream",
    "message": "File uploaded successfully"
}
```

#### 2. 生成下载URL
```bash
GET /api/v1/files/download/{task_id}/{filename}?expire_time=3600

# 响应
{
    "download_url": "https://...",
    "filename": "scene.ma",
    "object_key": "scenes/20240101/uuid/scene.ma",
    "expires_in": 3600
}
```

#### 3. 获取上传URL
```bash
POST /api/v1/files/upload-url?task_id=uuid&filename=scene.ma

# 响应
{
    "upload_url": "https://...",
    "object_key": "scenes/20240101/uuid/scene.ma",
    "filename": "scene.ma",
    "expires_in": 3600
}
```

### WebSocket API

#### 1. 建立连接
```bash
WebSocket: ws://localhost:8000/ws?user_id=123&token=xxx
```

#### 2. 获取连接统计
```bash
GET /stats

# 响应
{
    "total_connections": 5,
    "total_users": 3,
    "active_users": ["user1", "user2", "user3"]
}
```

#### 3. 发送测试通知
```bash
POST /send-notification?user_id=123&title=测试&message=这是一条测试消息&notification_type=info

# 响应
{
    "success": true,
    "message": "Notification sent to user 123"
}
```

## 安全建议

1. **OSS访问控制**：
   - 使用RAM角色管理OSS权限
   - 定期轮换AccessKey
   - 使用预签名URL限制访问时间

2. **WebSocket认证**：
   - 在生产环境中启用token验证
   - 实现连接心跳检测
   - 限制单用户最大连接数

3. **文件上传**：
   - 限制文件大小和类型
   - 扫描恶意文件
   - 使用病毒检测服务

## 测试

### 测试文件上传
```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?task_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/scene.ma"
```

### 测试WebSocket连接
使用浏览器控制台或工具如：
- Postman
- WebSocket King
- wscat

```bash
wscat -c "ws://localhost:8000/ws?user_id=123"
```

## 核心功能总结

### OSS功能
- 文件上传到阿里云OSS
- 生成预签名上传/下载URL
- 文件管理（删除、查询）
- 场景文件和渲染结果分类存储

### WebSocket功能
- 实时任务进度推送
- 任务状态变更通知
- 任务日志实时输出
- 系统通知推送
- 连接管理和心跳检测
- 支持单用户多连接
- 个人消息和广播消息
