# 批量文件上传任务管理系统 - 架构设计文档

> 创建时间：2024-10-22
> 版本：v1.0

## 一、业务场景

用户通过客户端批量上传文件到虚拟盘符，系统需要：
1. 客户端生成 **upload_manifest**（本地路径 → 虚拟路径映射）
2. 服务端上传到 OSS 后生成 **storage_manifest**（OSS 路径 → 虚拟路径映射）
3. 两个描述文件与 **任务ID** 绑定
4. 支持其他服务根据任务ID批量下载所有文件

## 二、核心设计原则

### 2.1 技术选型
- **描述文件格式**: JSON + 数据库（数据库存储结构化数据，JSON作为传输和备份格式）
- **去重策略**: 上传后检查（先上传到OSS，服务端计算MD5后检查去重）
- **任务管理**: 全功能（进度追踪 + 失败重试 + 分片上传 + 任务优先级）
- **使用场景**: 批量下载

### 2.2 数据流程
```
客户端扫描本地文件
    ↓
生成 upload_manifest
    ↓
POST /upload-tasks（创建任务）
    ↓
批量检查 MD5（秒传检测）
    ↓
上传文件到 OSS
    ↓
服务端生成 storage_manifest
    ↓
其他服务批量下载
```

## 三、数据模型设计

### 3.1 UploadTask（上传任务表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 外键 → users |
| drive_id | UUID | 外键 → drives |
| task_name | String(255) | 任务名称，如"项目文档上传 2024-10-22" |
| status | Enum | pending, uploading, completed, failed, cancelled |
| priority | Integer | 优先级 0-10，默认5 |
| total_files | Integer | 总文件数 |
| uploaded_files | Integer | 已上传文件数 |
| total_size | BigInteger | 总大小（字节） |
| uploaded_size | BigInteger | 已上传大小（字节） |
| upload_manifest | JSON | 客户端提交的上传描述 |
| storage_manifest | JSON | 服务端生成的存储描述 |
| error_message | Text | 错误信息 |
| retry_count | Integer | 重试次数，默认0 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| completed_at | DateTime | 完成时间 |

**关系**:
- belongs_to User
- belongs_to Drive
- has_many TaskFile

### 3.2 TaskFile（任务文件关系表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | UUID | 外键 → upload_tasks |
| file_id | UUID | 外键 → files（上传成功后关联） |
| local_path | String(1024) | 客户端本地路径 |
| target_folder_path | String(1024) | 目标文件夹虚拟路径 |
| file_name | String(255) | 文件名 |
| file_size | BigInteger | 文件大小（字节） |
| md5 | String(32) | MD5哈希值 |
| mime_type | String(100) | MIME类型 |
| status | Enum | pending, uploading, completed, failed, skipped |
| upload_progress | Float | 上传进度 0-100 |
| oss_key | String(512) | OSS对象键 |
| oss_url | String(1024) | OSS访问URL |
| chunk_info | JSON | 分片上传信息 |
| error_message | Text | 错误信息 |
| retry_count | Integer | 重试次数 |
| is_duplicated | Boolean | 是否秒传，默认False |
| duplicated_from | UUID | 外键 → files（引用的原文件） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| completed_at | DateTime | 完成时间 |

**关系**:
- belongs_to UploadTask
- belongs_to File (nullable)
- belongs_to File as duplicated_source (nullable)

## 四、描述文件格式规范

### 4.1 upload_manifest（客户端 → 服务端）

```json
{
  "task_name": "项目文档上传 2024-10-22",
  "drive_id": "uuid-drive-xxx",
  "priority": 5,
  "total_files": 3,
  "total_size": 10485760,
  "client_info": {
    "platform": "Windows 10",
    "version": "1.0.0",
    "ip": "192.168.1.100"
  },
  "files": [
    {
      "index": 0,
      "local_path": "C:/Users/xxx/Documents/report.pdf",
      "target_folder_path": "/项目文档/2024",
      "file_name": "report.pdf",
      "file_size": 1024000,
      "md5": "a1b2c3d4e5f6...",
      "mime_type": "application/pdf",
      "modified_time": "2024-10-22T10:30:00Z"
    },
    {
      "index": 1,
      "local_path": "D:/Photos/image.jpg",
      "target_folder_path": "/个人盘/图片",
      "file_name": "image.jpg",
      "file_size": 2048000,
      "md5": "b2c3d4e5f6a1...",
      "mime_type": "image/jpeg",
      "modified_time": "2024-10-22T10:31:00Z"
    }
  ]
}
```

### 4.2 storage_manifest（服务端生成）

```json
{
  "task_id": "uuid-task-yyy",
  "task_name": "项目文档上传 2024-10-22",
  "user_id": "uuid-user-zzz",
  "drive_id": "uuid-drive-xxx",
  "drive_name": "项目盘",
  "status": "completed",
  "summary": {
    "total_files": 3,
    "uploaded_files": 3,
    "failed_files": 0,
    "skipped_files": 0,
    "total_size": 10485760,
    "storage_saved": 2097152
  },
  "completed_at": "2024-10-22T14:35:20Z",
  "files": [
    {
      "file_id": "uuid-file-1",
      "task_file_id": "uuid-taskfile-1",
      "file_name": "report.pdf",
      "local_path": "C:/Users/xxx/Documents/report.pdf",
      "virtual_path": "/项目文档/2024/report.pdf",
      "folder_id": "uuid-folder-1",
      "oss_key": "uploads/2024/10/22/a1b2c3d4e5f6.pdf",
      "oss_url": "https://oss.aliyuncs.com/bucket/uploads/...",
      "file_size": 1024000,
      "md5": "a1b2c3d4e5f6...",
      "upload_status": "completed",
      "is_duplicated": false,
      "upload_duration": 2.5
    }
  ],
  "mappings": {
    "local_to_oss": {
      "C:/Users/xxx/Documents/report.pdf": "uploads/2024/10/22/a1b2c3d4e5f6.pdf",
      "D:/Photos/image.jpg": "uploads/2024/10/22/b2c3d4e5f6a1.jpg"
    },
    "local_to_virtual": {
      "C:/Users/xxx/Documents/report.pdf": "/项目文档/2024/report.pdf",
      "D:/Photos/image.jpg": "/个人盘/图片/image.jpg"
    },
    "oss_to_file_id": {
      "uploads/2024/10/22/a1b2c3d4e5f6.pdf": "uuid-file-1",
      "uploads/2024/10/22/b2c3d4e5f6a1.jpg": "uuid-file-2"
    }
  }
}
```

### 4.3 chunk_info（分片上传信息）

```json
{
  "upload_id": "oss-multipart-upload-xxx",
  "chunk_size": 5242880,
  "total_chunks": 20,
  "uploaded_chunks": [1, 2, 3, 4, 5],
  "chunk_etags": {
    "1": "etag-chunk-1",
    "2": "etag-chunk-2",
    "3": "etag-chunk-3"
  }
}
```

## 五、API 端点设计

### 5.1 上传任务管理 API

**路由前缀**: `/api/v1/upload-tasks`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/upload-tasks` | 创建上传任务 |
| GET | `/upload-tasks` | 获取任务列表（支持筛选状态） |
| GET | `/upload-tasks/{task_id}` | 获取任务详情 |
| GET | `/upload-tasks/{task_id}/files` | 获取任务文件列表 |
| GET | `/upload-tasks/{task_id}/progress` | 获取实时进度 |
| PUT | `/upload-tasks/{task_id}/cancel` | 取消任务 |
| DELETE | `/upload-tasks/{task_id}` | 删除任务 |
| POST | `/upload-tasks/{task_id}/export-manifest` | 导出 storage_manifest |

### 5.2 文件上传 API

**路由前缀**: `/api/v1/upload-tasks/{task_id}/files`

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/files/check` | 批量检查文件（秒传检测） |
| POST | `/files/{file_id}/upload` | 上传单个文件 |
| PUT | `/files/{file_id}/retry` | 重试失败的文件 |

**分片上传端点**:

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/files/{file_id}/multipart/init` | 初始化分片上传 |
| POST | `/files/{file_id}/multipart/upload` | 上传分片 |
| POST | `/files/{file_id}/multipart/complete` | 完成分片上传 |
| POST | `/files/{file_id}/multipart/abort` | 中止分片上传 |

### 5.3 批量下载 API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/upload-tasks/{task_id}/download` | 生成批量下载链接 |
| POST | `/upload-tasks/{task_id}/archive` | 创建 ZIP 打包任务 |

## 六、完整业务流程

### 阶段1: 创建任务

```
客户端                                  服务端
  │                                       │
  ├─ 1. 扫描本地文件                      │
  ├─ 2. 计算 MD5（可选前置）              │
  ├─ 3. 生成 upload_manifest             │
  │                                       │
  ├─ POST /upload-tasks ────────────────►│
  │    {upload_manifest}                  ├─ 创建 UploadTask (status=pending)
  │                                       ├─ 批量创建 TaskFile (status=pending)
  │                                       ├─ 解析 target_folder_path
  │◄───────────────────── task_id ───────┤ └─ 自动创建不存在的 Folder
```

### 阶段2: 秒传检查

```
客户端                                  服务端
  │                                       │
  ├─ POST /files/check ─────────────────►│
  │    {md5_list: [...]}                  ├─ 查询 File 表 WHERE md5 IN (...)
  │                                       ├─ 返回已存在的文件列表
  │◄────────── {existing_files} ─────────┤
  │                                       │
  ├─ 对于已存在的文件：                   │
  │    跳过上传                            │
  │                                       │
  │    服务端更新 TaskFile:               │
  │    - status = skipped                 │
  │    - is_duplicated = true             │
  │    - duplicated_from = existing_file_id│
  │    - 创建新的 File 记录（引用相同 oss_key）│
```

### 阶段3: 上传文件

**小文件直接上传 (<5MB)**:

```
客户端                                  服务端
  │                                       │
  ├─ POST /files/{file_id}/upload ──────►│
  │    FormData(file: binary)             ├─ 1. 上传到 OSS
  │                                       ├─ 2. 计算 MD5
  │                                       ├─ 3. 检查去重
  │                                       ├─ 4. 创建/更新 File 记录
  │                                       ├─ 5. 更新 TaskFile:
  │                                       │    - status = completed
  │                                       │    - oss_key, oss_url, file_id
  │                                       ├─ 6. 更新 UploadTask 进度
  │◄────────── {file_info} ──────────────┤ └─ 7. 记录 FileOperation 日志
```

**大文件分片上传 (>=5MB)**:

```
客户端                                  服务端
  │                                       │
  ├─ 1. POST /multipart/init ───────────►│
  │    {file_size, file_name}             ├─ 初始化 OSS 分片上传
  │◄────── {upload_id, chunk_size} ──────┤ ├─ 更新 TaskFile.chunk_info
  │                                       │
  ├─ 2. 循环上传分片 (5MB/片)             │
  │    POST /multipart/upload ───────────►│
  │    {chunk_index, chunk_data}          ├─ 上传分片到 OSS
  │◄────── {chunk_etag} ─────────────────┤ ├─ 更新 chunk_info
  │                                       │ └─ 更新 upload_progress
  │                                       │
  ├─ 3. POST /multipart/complete ────────►│
  │    {chunk_etags: [...]}               ├─ 完成 OSS 分片上传
  │                                       ├─ 计算 MD5
  │                                       ├─ 检查去重
  │                                       ├─ 创建 File 记录
  │◄────────── {file_info} ──────────────┤ └─ 更新 TaskFile
```

### 阶段4: 任务完成

```
服务端自动触发（当所有 TaskFile.status in [completed, skipped]）:

1. 聚合统计数据
2. 生成 storage_manifest JSON:
   - 汇总所有文件信息
   - 生成三个映射表（local_to_oss, local_to_virtual, oss_to_file_id）
3. 更新 UploadTask:
   - status = completed
   - storage_manifest = {...}
   - completed_at = now()
4. 记录 FileOperation 日志（operation_type = UPLOAD）
```

### 阶段5: 批量下载

```
其他服务                                服务端
  │                                       │
  ├─ GET /upload-tasks/{task_id} ───────►│
  │                                       ├─ 获取 storage_manifest
  │◄────── {storage_manifest} ───────────┤
  │                                       │
  ├─ 解析 manifest.files                  │
  ├─ 逐个下载 OSS 文件                    │
  │                                       │
  │ 或者：                                │
  │                                       │
  ├─ POST /upload-tasks/{task_id}/archive►│
  │    {format: "zip"}                    ├─ 从 OSS 下载所有文件
  │                                       ├─ 打包成 ZIP
  │                                       ├─ 上传到临时区域
  │◄────── {download_url, expires} ──────┤ └─ 返回临时下载链接（1小时有效）
```

## 七、关键技术特性

### 7.1 进度追踪

**任务级别进度**:
```python
progress_percentage = (uploaded_files / total_files) * 100
size_progress = (uploaded_size / total_size) * 100
```

**文件级别进度**:
```python
# 直接上传
upload_progress = (uploaded_bytes / file_size) * 100

# 分片上传
upload_progress = (len(uploaded_chunks) / total_chunks) * 100
```

**实时更新机制**:
- HTTP轮询：客户端定期调用 `GET /upload-tasks/{task_id}/progress`
- WebSocket（可选）：服务端主动推送进度更新

### 7.2 失败重试机制

**自动重试**:
```python
MAX_AUTO_RETRY = 3

if upload_failed and retry_count < MAX_AUTO_RETRY:
    retry_count += 1
    status = "pending"  # 重新加入队列
else:
    status = "failed"
```

**手动重试**:
```
PUT /files/{file_id}/retry
→ 重置 status = "pending", error_message = None
→ 可以重新调用上传接口
```

### 7.3 分片上传支持

**触发条件**: file_size >= 5MB

**分片策略**:
- chunk_size = 5MB
- 并发上传：最多3个分片同时上传
- 断点续传：已上传的分片保存在 chunk_info 中

**OSS集成**:
```python
# 使用阿里云 OSS Multipart Upload API
1. InitiateMultipartUpload → upload_id
2. UploadPart (循环) → part_etag
3. CompleteMultipartUpload → final_etag
```

### 7.4 任务优先级调度

**优先级规则**:
- priority = 10: 最高优先级（VIP用户）
- priority = 5: 默认优先级
- priority = 0: 最低优先级

**实现方式**:
- 可选：使用 Celery/RQ 任务队列
- 简单实现：按 priority DESC, created_at ASC 排序处理

### 7.5 秒传优化

**去重检查**:
```python
# 上传文件到 OSS 后
uploaded_file_md5 = calculate_md5(oss_file)

existing_file = db.query(File).filter(File.md5 == uploaded_file_md5).first()

if existing_file:
    # 删除刚上传的 OSS 文件
    oss_client.delete_object(oss_key)

    # 创建新的 File 记录（引用相同的 oss_key）
    new_file = File(
        oss_key=existing_file.oss_key,
        oss_url=existing_file.oss_url,
        md5=uploaded_file_md5,
        ...
    )

    # 更新 TaskFile
    task_file.is_duplicated = True
    task_file.duplicated_from = existing_file.id
```

**节省统计**:
```python
storage_saved = sum(
    file.file_size
    for file in task.files
    if file.is_duplicated
)
```

## 八、实施计划

### Phase 1: 数据模型扩展
- [ ] 创建 UploadTask 模型
- [ ] 创建 TaskFile 模型
- [ ] 生成并应用数据库迁移
- [ ] 更新 models/__init__.py

### Phase 2: Schemas 定义
- [ ] 创建 upload_task.py schemas
  - UploadTaskCreate, UploadTaskUpdate, UploadTaskResponse
  - UploadManifest, StorageManifest
  - TaskFileResponse, TaskFileListResponse
- [ ] 创建 file_upload.py schemas
  - FileCheckRequest, FileCheckResponse
  - FileUploadRequest, FileUploadResponse
  - MultipartInitRequest, MultipartInitResponse
  - ChunkUploadRequest, ChunkUploadResponse

### Phase 3: Service 层实现
- [ ] 创建 upload_task_service.py
  - create_task, get_task, list_tasks
  - update_progress, complete_task
  - generate_storage_manifest
- [ ] 创建 file_upload_service.py
  - check_files_exist (秒传检查)
  - upload_file (直接上传)
  - init_multipart, upload_chunk, complete_multipart (分片上传)
  - retry_file
- [ ] 创建 batch_download_service.py
  - generate_download_links
  - create_archive (打包下载)

### Phase 4: API 端点实现
- [ ] 创建 upload_tasks.py
  - POST /upload-tasks
  - GET /upload-tasks, GET /upload-tasks/{task_id}
  - GET /upload-tasks/{task_id}/files
  - GET /upload-tasks/{task_id}/progress
  - PUT /upload-tasks/{task_id}/cancel
  - DELETE /upload-tasks/{task_id}
  - POST /upload-tasks/{task_id}/export-manifest
- [ ] 创建 file_uploads.py
  - POST /files/check
  - POST /files/{file_id}/upload
  - PUT /files/{file_id}/retry
  - POST /files/{file_id}/multipart/* (4个端点)
- [ ] 添加批量下载端点到 upload_tasks.py
  - GET /upload-tasks/{task_id}/download
  - POST /upload-tasks/{task_id}/archive

### Phase 5: 集成与测试
- [ ] 路由注册
- [ ] 端到端测试
- [ ] 性能测试

## 九、注意事项

### 9.1 并发控制
- 同一任务的多个文件可以并发上传
- 但需要加锁更新 UploadTask 的进度字段（uploaded_files, uploaded_size）

### 9.2 事务处理
- 创建任务时，UploadTask 和 TaskFile 的创建需要在同一事务中
- 完成任务时，更新所有相关记录需要在同一事务中

### 9.3 错误处理
- 所有 OSS 操作需要捕获异常并记录到 error_message
- 网络错误、超时等需要触发重试机制

### 9.4 性能优化
- 批量检查文件时，使用 `WHERE md5 IN (...)` 一次查询
- 生成 storage_manifest 时，使用 eager loading 加载关联数据

### 9.5 安全考虑
- 上传文件前检查文件类型和大小限制
- 下载链接需要签名和过期时间控制
- 检查用户权限（只能操作自己的任务）

## 十、扩展功能（可选）

- [ ] WebSocket 实时进度推送
- [ ] 任务暂停/恢复功能
- [ ] 上传速度限制（带宽控制）
- [ ] 上传完成后的回调通知
- [ ] 任务调度队列（Celery集成）
- [ ] 上传历史记录和统计报表

---

**文档状态**: ✅ 架构设计完成，等待实施
