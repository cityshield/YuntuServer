# 盛世云图后端服务 (YuntuServer)

Maya 云渲染平台后端API服务

## 🏗️ 技术栈

- **Framework**: FastAPI 0.104+ (Python 3.11+)
- **Database**: PostgreSQL 15 + SQLAlchemy 2.0 (AsyncIO)
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery + Redis
- **File Storage**: 阿里云 OSS
- **Auth**: JWT (python-jose)
- **Container**: Docker + Docker Compose
- **Web Server**: Uvicorn + Nginx

## 📂 项目结构

```
yuntu-server/
├── app/
│   ├── api/v1/          # API路由
│   ├── core/            # 核心功能（security, middleware）
│   ├── db/              # 数据库配置
│   ├── models/          # SQLAlchemy模型 ✅
│   ├── schemas/         # Pydantic Schemas
│   ├── services/        # 业务逻辑层
│   ├── tasks/           # Celery异步任务
│   ├── utils/           # 工具函数 ✅
│   ├── config.py        # 配置管理 ✅
│   └── main.py          # FastAPI应用入口 ✅
├── alembic/             # 数据库迁移
├── docker/              # Docker配置
├── logs/                # 日志目录
└── requirements.txt     # Python依赖 ✅
```

## ✅ 已完成（100%）

### 核心框架
1. ✅ 项目目录结构
2. ✅ 配置管理（config.py, .env.example）
3. ✅ 数据库模型（User, Task, TaskLog, Transaction, Bill, RefreshToken）
4. ✅ 核心工具（security.py, logger.py, redis_client.py）
5. ✅ FastAPI应用入口（main.py）
6. ✅ 依赖管理（requirements.txt）

### API功能
7. ✅ Pydantic Schemas（完整的请求/响应验证）
8. ✅ 依赖注入系统（get_current_user, 权限检查）
9. ✅ 认证API（注册、登录、Token刷新、登出）
10. ✅ 用户API（信息、资料、余额、充值、交易、账单）
11. ✅ 任务API（CRUD、暂停/恢复/取消、日志）
12. ✅ 文件API（上传、下载、OSS集成）
13. ✅ WebSocket API（实时推送）

### 业务逻辑
14. ✅ 认证服务（auth_service.py）
15. ✅ 用户服务（user_service.py）
16. ✅ 任务服务（task_service.py）
17. ✅ 计费服务（billing_service.py）
18. ✅ 文件服务（file_service.py + oss_service.py）
19. ✅ WebSocket服务（websocket_service.py）

### 异步任务
20. ✅ Celery配置（celery_app.py）
21. ✅ 模拟渲染任务（render_tasks.py）
22. ✅ 任务队列管理

### 部署配置
23. ✅ Docker Compose（完整的7个服务）
24. ✅ Dockerfile（API + Worker）
25. ✅ Nginx配置（反向代理 + WebSocket + SSL）
26. ✅ 数据库迁移（Alembic）
27. ✅ 开发环境脚本（start_dev.sh）
28. ✅ 生产环境脚本（deploy.sh）
29. ✅ 部署指南（DEPLOYMENT_GUIDE.md）

## 📊 数据库模型

### User（用户）
- 用户名、邮箱、手机号
- 密码哈希
- 余额、会员等级
- 创建/更新时间

### Task（任务）
- 任务名称、场景文件
- Maya版本、渲染器
- 状态、优先级、进度
- 帧范围、分辨率
- 费用信息

### TaskLog（任务日志）
- 日志级别、消息
- 关联任务ID

### Transaction（交易记录）
- 类型（充值/消费/退款）
- 金额、余额
- 描述

### Bill（账单）
- 关联任务
- 金额、描述

### RefreshToken（刷新令牌）
- Token字符串
- 过期时间

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd YuntuServer

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填写配置
# - DATABASE_URL
# - REDIS_URL
# - SECRET_KEY
# - OSS配置
```

### 3. 启动服务（开发环境）

```bash
# 直接运行
python app/main.py

# 或使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Docker部署（生产环境）

```bash
cd docker
docker-compose up -d
```

## 📝 API端点

### 认证相关 `/api/v1/auth`
- `POST /register` - 用户注册
- `POST /login` - 用户登录
- `POST /refresh` - 刷新Token
- `POST /logout` - 登出

### 用户相关 `/api/v1/users`
- `GET /me` - 获取当前用户信息
- `PUT /me` - 更新用户资料
- `GET /balance` - 获取余额
- `POST /recharge` - 账户充值
- `GET /transactions` - 交易记录
- `GET /bills` - 账单记录

### 任务相关 `/api/v1/tasks`
- `POST /` - 创建任务
- `GET /` - 获取任务列表
- `GET /{task_id}` - 获取任务详情
- `PUT /{task_id}/pause` - 暂停任务
- `PUT /{task_id}/resume` - 恢复任务
- `PUT /{task_id}/cancel` - 取消任务
- `DELETE /{task_id}` - 删除任务
- `GET /{task_id}/logs` - 获取任务日志

### 文件相关 `/api/v1/files`
- `POST /upload` - 上传场景文件
- `GET /download/{task_id}/{filename}` - 下载结果

### WebSocket `/ws`
- 任务进度更新
- 任务状态变化
- 任务日志推送
- 系统通知

## 🔐 认证机制

采用JWT双Token机制：
- **Access Token**: 30分钟有效期，用于API请求
- **Refresh Token**: 7天有效期，用于刷新Access Token

请求头格式：
```
Authorization: Bearer <access_token>
```

## 🐳 Docker服务

- `postgres` - PostgreSQL 15 数据库
- `redis` - Redis 7 缓存/队列
- `api` - FastAPI 应用
- `celery-worker` - Celery 任务处理
- `celery-beat` - Celery 定时任务
- `flower` - Celery 监控面板
- `nginx` - 反向代理

## 📱 客户端集成

客户端地址：`../YuntuClient`

API基础URL：
- 开发环境：`http://localhost:8000/api/v1`
- 生产环境：`https://api.yuntucv.com/api/v1`

WebSocket URL：
- 开发环境：`ws://localhost:8000/ws`
- 生产环境：`wss://api.yuntucv.com/ws`

## 🛠️ 开发命令

```bash
# 启动开发服务器
python app/main.py

# 运行测试
pytest

# 代码格式化
black app/

# 代码检查
flake8 app/

# 数据库迁移
alembic upgrade head

# 创建迁移
alembic revision --autogenerate -m "description"
```

## 📖 文档

- API文档（Swagger）: `http://localhost:8000/docs`
- API文档（ReDoc）: `http://localhost:8000/redoc`
- 健康检查: `http://localhost:8000/health`

## 🎯 下一步工作

当前项目已经完成了基础框架搭建，接下来Agent将并行完成：

1. **所有API端点实现** - auth, users, tasks, files
2. **服务层代码** - 业务逻辑封装
3. **Pydantic Schemas** - 请求/响应验证
4. **阿里云OSS集成** - 文件上传下载
5. **WebSocket服务** - 实时推送
6. **Celery任务** - 模拟渲染任务
7. **Docker完整配置** - 生产环境部署
8. **数据库迁移** - Alembic配置

## 📞 联系方式

项目地址：`/Users/pretty/Documents/Workspace/YuntuServer`
客户端地址：`/Users/pretty/Documents/Workspace/YuntuClient`
API域名：`api.yuntucv.com`

---

🤖 Generated with Claude Code
