# 盛世云图后端服务 - 完整部署指南

## 🎉 项目完成状态

所有核心功能已全部完成，可以立即部署使用！

---

## 📊 已完成功能清单

### ✅ 核心框架（100%）
- [x] FastAPI应用配置
- [x] 数据库模型（6个表）
- [x] Pydantic Schemas（完整的数据验证）
- [x] 依赖注入系统
- [x] 异常处理和日志

### ✅ 认证系统（100%）
- [x] 用户注册
- [x] 用户登录（用户名/邮箱）
- [x] JWT Token（Access + Refresh）
- [x] Token刷新
- [x] 用户登出

### ✅ 用户管理（100%）
- [x] 获取用户信息
- [x] 更新用户资料
- [x] 查看余额
- [x] 账户充值
- [x] 交易记录查询
- [x] 账单记录查询

### ✅ 任务管理（100%）
- [x] 创建任务
- [x] 任务列表（分页、筛选）
- [x] 任务详情
- [x] 暂停/恢复任务
- [x] 取消任务
- [x] 删除任务
- [x] 任务日志查询
- [x] 任务状态机

### ✅ 文件服务（100%）
- [x] 阿里云OSS集成
- [x] 场景文件上传
- [x] 渲染结果下载
- [x] 预签名URL生成
- [x] 文件管理

### ✅ 实时通信（100%）
- [x] WebSocket连接管理
- [x] 任务进度推送
- [x] 任务状态推送
- [x] 任务日志推送
- [x] 系统通知推送

### ✅ 异步任务（100%）
- [x] Celery配置
- [x] 模拟渲染任务
- [x] 任务队列管理
- [x] 进度更新
- [x] 费用计算

### ✅ 部署配置（100%）
- [x] Docker Compose
- [x] Nginx配置
- [x] 数据库迁移（Alembic）
- [x] 开发环境脚本
- [x] 生产环境脚本

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│                   客户端                         │
│              (Qt C++ Application)               │
└─────────────┬───────────────────────────────────┘
              │ HTTPS/WSS
┌─────────────▼───────────────────────────────────┐
│              Nginx反向代理                       │
│     api.yuntucv.com (SSL/TLS终端)              │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│           FastAPI应用 (8000)                    │
│  ┌──────────────────────────────────────────┐  │
│  │ 认证 │ 用户 │ 任务 │ 文件 │ WebSocket   │  │
│  └──────────────────────────────────────────┘  │
└──┬────────┬──────────┬───────────────┬─────────┘
   │        │          │               │
   │        │          │               │
┌──▼─────┐ ┌▼────────┐ ┌▼────────┐   ┌▼────────┐
│PostgreSQL│ │ Redis   │ │阿里云OSS│   │ Celery  │
│  数据库  │ │缓存/队列│ │ 文件存储│   │  Workers│
└─────────┘ └─────────┘ └─────────┘   └─────────┘
```

---

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Docker & Docker Compose
- 阿里云OSS账号（Access Key + Secret Key）
- PostgreSQL 15（Docker提供）
- Redis 7（Docker提供）

---

## 📝 配置步骤

### 1. 克隆或使用项目

```bash
cd /Users/pretty/Documents/Workspace/YuntuServer
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env  # 或使用其他编辑器
```

**必须配置的环境变量：**

```env
# 数据库（生产环境）
DATABASE_URL=postgresql+asyncpg://yuntu:your_password@postgres:5432/yuntu_db

# JWT密钥（必须修改！）
SECRET_KEY=请替换为至少32位的随机字符串

# 阿里云OSS（必须配置）
OSS_ACCESS_KEY_ID=你的AccessKey
OSS_ACCESS_KEY_SECRET=你的SecretKey
OSS_BUCKET_NAME=yuntu-bucket
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BASE_URL=https://yuntu-bucket.oss-cn-beijing.aliyuncs.com
```

**生成安全的SECRET_KEY：**

```bash
# 方法1：使用Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 方法2：使用OpenSSL
openssl rand -hex 32
```

---

## 🐳 Docker部署（推荐）

### 首次部署

```bash
# 1. 进入项目目录
cd /Users/pretty/Documents/Workspace/YuntuServer

# 2. 运行部署脚本
./scripts/deploy.sh

# 3. 选择选项 1 - 首次部署
# 脚本会自动：
#   - 创建必要的目录
#   - 构建Docker镜像
#   - 启动所有服务
#   - 运行数据库迁移
```

### 查看服务状态

```bash
./scripts/deploy.sh  # 选择选项 6
```

**预期输出：**
```
✓ postgres      - running
✓ redis         - running
✓ api           - running
✓ celery-worker - running
✓ celery-beat   - running
✓ flower        - running
✓ nginx         - running
```

### 查看服务日志

```bash
./scripts/deploy.sh  # 选择选项 7
```

### 更新部署

```bash
./scripts/deploy.sh  # 选择选项 2
```

---

## 💻 开发环境部署

### 1. 创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置本地数据库

**选项A：使用Docker（推荐）**

```bash
# 只启动数据库和Redis
docker-compose -f docker/docker-compose.yml up -d postgres redis
```

**选项B：本地安装**

- 安装PostgreSQL 15
- 安装Redis 7
- 修改.env中的DATABASE_URL为localhost

### 4. 运行数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "Initial migration"

# 应用迁移
alembic upgrade head
```

### 5. 启动服务

```bash
./scripts/start_dev.sh  # 选择选项 5（启动全部服务）
```

**或者手动启动：**

```bash
# 终端1：FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2：Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info -Q render

# 终端3：Celery Beat
celery -A app.tasks.celery_app beat --loglevel=info

# 终端4：Flower（可选）
celery -A app.tasks.celery_app flower --port=5555
```

---

## 🔍 验证部署

### 1. 健康检查

```bash
curl http://localhost/health
# 或
curl https://api.yuntucv.com/health
```

**预期响应：**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "YuntuServer",
  "domain": "api.yuntucv.com"
}
```

### 2. API文档

访问：`http://localhost/docs` 或 `https://api.yuntucv.com/docs`

### 3. Celery监控

访问：`http://localhost:5555` 或 `https://api.yuntucv.com:5555`

### 4. 测试用户注册

```bash
curl -X POST "http://localhost/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "phone": "13800138000"
  }'
```

### 5. 测试WebSocket连接

```bash
# 使用wscat（需要先安装：npm install -g wscat）
wscat -c ws://localhost/ws
```

---

## 📊 API端点总览

### 认证 `/api/v1/auth`
- `POST /register` - 用户注册
- `POST /login` - 用户登录
- `POST /refresh` - 刷新Token
- `POST /logout` - 用户登出

### 用户 `/api/v1/users`
- `GET /me` - 获取当前用户
- `PUT /me` - 更新用户资料
- `GET /balance` - 获取余额
- `POST /recharge` - 账户充值
- `GET /transactions` - 交易记录
- `GET /bills` - 账单记录

### 任务 `/api/v1/tasks`
- `POST /` - 创建任务
- `GET /` - 任务列表
- `GET /{task_id}` - 任务详情
- `PUT /{task_id}/pause` - 暂停任务
- `PUT /{task_id}/resume` - 恢复任务
- `PUT /{task_id}/cancel` - 取消任务
- `DELETE /{task_id}` - 删除任务
- `GET /{task_id}/logs` - 任务日志

### 文件 `/api/v1/files`
- `POST /upload` - 上传文件
- `GET /download/{task_id}/{filename}` - 下载文件

### WebSocket `/ws`
- 实时任务进度
- 实时任务状态
- 实时日志推送
- 系统通知

---

## 🔐 SSL证书配置

### 1. 获取证书

**方法A：Let's Encrypt（免费）**

```bash
# 安装certbot
sudo apt-get install certbot

# 生成证书
sudo certbot certonly --standalone -d api.yuntucv.com
```

**方法B：阿里云SSL证书**

- 在阿里云控制台申请免费SSL证书
- 下载Nginx格式证书

### 2. 配置证书

```bash
# 复制证书到项目目录
mkdir -p ssl
cp /path/to/fullchain.pem ssl/
cp /path/to/privkey.pem ssl/
```

### 3. 修改Nginx配置

编辑 `docker/nginx.conf`，取消HTTPS相关配置的注释。

### 4. 重启Nginx

```bash
docker-compose restart nginx
```

---

## 📈 性能优化建议

### 1. 数据库优化

```sql
-- 创建索引（已在模型中定义）
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_task_logs_task_id ON task_logs(task_id);
```

### 2. Redis优化

```bash
# 增加最大内存
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### 3. Celery优化

```python
# 调整Worker数量（根据CPU核心数）
celery -A app.tasks.celery_app worker -c 8
```

### 4. Nginx优化

```nginx
# 启用缓存
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g;
```

---

## 🐛 故障排查

### 问题1：数据库连接失败

```bash
# 检查PostgreSQL是否运行
docker-compose ps postgres

# 检查数据库连接
docker-compose exec postgres psql -U yuntu -d yuntu_db
```

### 问题2：Redis连接失败

```bash
# 检查Redis是否运行
docker-compose ps redis

# 测试连接
docker-compose exec redis redis-cli ping
```

### 问题3：OSS上传失败

- 检查Access Key是否正确
- 检查Bucket名称和Endpoint
- 检查网络连接

### 问题4：Celery任务不执行

```bash
# 检查Celery Worker日志
docker-compose logs -f celery-worker

# 检查任务队列
docker-compose exec redis redis-cli LLEN celery
```

### 问题5：WebSocket连接失败

- 检查Nginx配置中的WebSocket支持
- 检查防火墙设置
- 确保客户端使用正确的WebSocket URL

---

## 📦 数据备份

### 1. 数据库备份

```bash
# 备份
docker-compose exec postgres pg_dump -U yuntu yuntu_db > backup_$(date +%Y%m%d).sql

# 恢复
docker-compose exec -T postgres psql -U yuntu yuntu_db < backup_20251014.sql
```

### 2. Redis备份

```bash
# Redis会自动保存AOF文件到redis_data卷
docker-compose exec redis redis-cli BGSAVE
```

---

## 🔄 更新和维护

### 代码更新

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 更新依赖
pip install -r requirements.txt

# 3. 运行数据库迁移
alembic upgrade head

# 4. 重启服务
./scripts/deploy.sh  # 选择选项 5（重启）
```

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "Add new column"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

---

## 📞 技术支持

### 项目信息
- **项目路径**: `/Users/pretty/Documents/Workspace/YuntuServer`
- **客户端路径**: `/Users/pretty/Documents/Workspace/YuntuClient`
- **API域名**: `api.yuntucv.com`
- **WebSocket**: `wss://api.yuntucv.com/ws`

### 日志位置
- **应用日志**: `logs/app.log`
- **Nginx日志**: `docker logs yuntu-nginx`
- **数据库日志**: `docker logs yuntu-postgres`
- **Celery日志**: `docker logs yuntu-celery-worker`

---

## 🎯 下一步建议

1. **安全加固**
   - 配置SSL证书
   - 启用防火墙
   - 配置速率限制
   - 添加API密钥验证

2. **监控和告警**
   - 集成Prometheus + Grafana
   - 配置Sentry错误追踪
   - 设置告警规则

3. **性能优化**
   - 启用Redis缓存
   - 配置CDN加速静态资源
   - 数据库查询优化

4. **功能扩展**
   - 添加邮箱验证
   - 实现忘记密码功能
   - 添加OAuth第三方登录
   - 实现真实的Maya渲染集成

---

🎉 **恭喜！后端服务已完成并可以部署使用！**

---

📅 **创建日期**: 2025年10月14日
🤖 **Generated with**: Claude Code
