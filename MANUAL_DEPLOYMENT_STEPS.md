# YuntuServer 手动部署完整步骤

## 服务器信息
- **IP地址**: 59.110.51.85
- **SSH端口**: 777
- **用户**: root
- **部署目录**: /var/www/api/
- **域名**: api.yuntucv.com

---

## 📋 部署检查清单

在开始之前，请确保：
- [ ] 域名 api.yuntucv.com 已解析到 59.110.51.85
- [ ] 本地已配置好 .env 文件
- [ ] 服务器 777 端口 SSH 可访问
- [ ] 服务器防火墙开放 80 端口（HTTP）

---

## 第一步：本地打包项目（在 Mac 上执行）

### 1.1 打包项目文件

```bash
cd /Users/pretty/Documents/Workspace/YuntuServer

# 创建部署包
tar -czf yuntu-server-deploy.tar.gz \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.db' \
    --exclude='*.db-journal' \
    --exclude='logs/*' \
    --exclude='temp_uploads' \
    --exclude='.pytest_cache' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    app/ alembic/ scripts/ deployment/ \
    requirements.txt alembic.ini .env

# 确认打包成功
ls -lh yuntu-server-deploy.tar.gz
```

### 1.2 上传到服务器

```bash
# 使用 scp 上传（指定端口 777）
scp -P 777 yuntu-server-deploy.tar.gz root@59.110.51.85:/tmp/

# 输入密码: Yuntu123
```

---

## 第二步：服务器环境准备（SSH 到服务器执行）

### 2.1 连接到服务器

```bash
# 在本地 Mac 执行
ssh -p 777 root@59.110.51.85

# 输入密码: Yuntu123
```

### 2.2 更新系统

```bash
# 更新软件包列表
apt update && apt upgrade -y
```

### 2.3 安装 Python 3.10

```bash
# 检查 Python 版本
python3 --version

# 如果版本低于 3.10，安装 Python 3.10
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# 验证安装
python3.10 --version
```

### 2.4 安装 PostgreSQL 14

```bash
# 安装 PostgreSQL
apt install -y postgresql-14 postgresql-contrib-14

# 启动并设置开机自启
systemctl start postgresql
systemctl enable postgresql

# 验证运行状态
systemctl status postgresql
```

### 2.5 配置 PostgreSQL 数据库

```bash
# 切换到 postgres 用户并创建数据库
sudo -u postgres psql << 'EOF'
-- 创建数据库
CREATE DATABASE yuntu_production;

-- 创建用户（使用强密码）
CREATE USER yuntu_user WITH ENCRYPTED PASSWORD 'YuntuDB2025!@#';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE yuntu_production TO yuntu_user;

-- 连接到数据库
\c yuntu_production

-- 授予 schema 权限
GRANT ALL ON SCHEMA public TO yuntu_user;

-- 退出
\q
EOF

# 测试连接
psql -U yuntu_user -d yuntu_production -h localhost -W
# 输入密码: YuntuDB2025!@#
# 成功后输入 \q 退出
```

### 2.6 安装 Redis

```bash
# 安装 Redis
apt install -y redis-server

# 配置 Redis 密码
echo "requirepass YuntuRedis2025!@#" >> /etc/redis/redis.conf

# 重启 Redis
systemctl restart redis-server
systemctl enable redis-server

# 测试连接
redis-cli
AUTH YuntuRedis2025!@#
PING
# 应该返回 PONG
exit
```

### 2.7 安装 Nginx

```bash
# 安装 Nginx
apt install -y nginx

# 启动并设置开机自启
systemctl start nginx
systemctl enable nginx

# 验证运行
systemctl status nginx
```

---

## 第三步：部署应用（服务器上执行）

### 3.1 创建部署目录

```bash
# 创建目录
mkdir -p /var/www/api
cd /var/www/api

# 创建日志目录
mkdir -p logs
mkdir -p temp_uploads
```

### 3.2 解压项目文件

```bash
# 解压
tar -xzf /tmp/yuntu-server-deploy.tar.gz -C /var/www/api/

# 验证文件
ls -la

# 应该看到: app/ alembic/ scripts/ requirements.txt alembic.ini .env
```

### 3.3 修改 .env 配置文件

```bash
# 编辑配置文件
vim /var/www/api/.env

# 修改以下配置项：
```

**修改内容**：

```bash
# Database (修改为生产环境数据库)
DATABASE_URL=postgresql+asyncpg://yuntu_user:YuntuDB2025!@#@localhost:5432/yuntu_production

# Redis (修改密码)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=YuntuRedis2025!@#

# 日志路径（修改为绝对路径）
LOG_FILE=/var/www/api/logs/app.log

# OSS 回调（使用 HTTP，因为暂无 SSL）
OSS_CALLBACK_URL=http://api.yuntucv.com/api/v1/oss-callback/upload-complete
OSS_CALLBACK_HOST=api.yuntucv.com

# CORS（添加生产域名）
CORS_ORIGINS=["http://api.yuntucv.com","http://59.110.51.85","http://localhost:5173"]

# 其他配置保持不变
```

保存并退出（按 ESC，输入 `:wq`，回车）

### 3.4 创建 Python 虚拟环境

```bash
cd /var/www/api

# 创建虚拟环境
python3.10 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证 Python 版本
python --version
# 应该显示 Python 3.10.x
```

### 3.5 安装 Python 依赖

```bash
# 确保虚拟环境已激活（提示符前面应该有 (venv)）
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 等待安装完成（可能需要 5-10 分钟）
```

### 3.6 运行数据库迁移

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 运行迁移
alembic upgrade head

# 应该看到迁移成功的消息
```

---

## 第四步：配置系统服务（服务器上执行）

### 4.1 创建 Systemd 服务文件

```bash
# 复制 Systemd 配置
cp /var/www/api/deployment/systemd/yuntu-server.service /etc/systemd/system/

# 编辑服务配置（如果需要调整）
vim /etc/systemd/system/yuntu-server.service

# 检查以下内容是否正确：
# - WorkingDirectory=/var/www/api
# - Environment="PATH=/var/www/api/venv/bin"
# - ExecStart=/var/www/api/venv/bin/gunicorn...
```

### 4.2 设置文件权限

```bash
# 创建 www-data 用户（如果不存在）
id www-data || useradd -r -s /bin/false www-data

# 设置目录权限
chown -R www-data:www-data /var/www/api
chmod -R 755 /var/www/api
chmod -R 775 /var/www/api/logs
chmod -R 775 /var/www/api/temp_uploads
```

### 4.3 启动应用服务

```bash
# 重载 systemd
systemctl daemon-reload

# 启动服务
systemctl start yuntu-server

# 查看状态
systemctl status yuntu-server

# 如果启动失败，查看日志
journalctl -u yuntu-server -n 50 --no-pager

# 设置开机自启
systemctl enable yuntu-server
```

### 4.4 验证服务运行

```bash
# 检查端口监听
netstat -tlnp | grep 8000
# 应该看到: 127.0.0.1:8000 LISTEN

# 测试本地访问
curl http://127.0.0.1:8000/health
# 应该返回: {"status":"healthy",...}
```

---

## 第五步：配置 Nginx（服务器上执行）

### 5.1 创建 Nginx 配置文件

```bash
# 复制 HTTP 版本的配置（无需 SSL）
cp /var/www/api/deployment/nginx/api.yuntucv.com.http.conf /etc/nginx/sites-available/api.yuntucv.com

# 创建软链接
ln -s /etc/nginx/sites-available/api.yuntucv.com /etc/nginx/sites-enabled/

# 删除默认配置（可选）
rm /etc/nginx/sites-enabled/default

# 测试 Nginx 配置
nginx -t

# 应该显示: syntax is ok, test is successful
```

### 5.2 重载 Nginx

```bash
# 重载配置
systemctl reload nginx

# 验证运行状态
systemctl status nginx
```

### 5.3 配置防火墙

```bash
# 如果使用 UFW
ufw allow 80/tcp
ufw allow 777/tcp
ufw status

# 如果使用 iptables
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 777 -j ACCEPT
iptables-save
```

---

## 第六步：验证部署（在 Mac 或浏览器执行）

### 6.1 测试 HTTP 接口

```bash
# 测试 IP 访问
curl http://59.110.51.85/health

# 测试域名访问（如果域名已解析）
curl http://api.yuntucv.com/health

# 预期响应：
# {"status":"healthy","timestamp":"2025-10-25T..."}
```

### 6.2 浏览器访问

访问以下 URL：

- **API 文档**: http://api.yuntucv.com/docs
- **健康检查**: http://api.yuntucv.com/health
- **API 根路径**: http://api.yuntucv.com/api/v1/ping

### 6.3 查看日志

```bash
# 应用日志
tail -f /var/www/api/logs/app.log

# Systemd 日志
journalctl -u yuntu-server -f

# Nginx 访问日志
tail -f /var/log/nginx/api.yuntucv.com.access.log

# Nginx 错误日志
tail -f /var/log/nginx/api.yuntucv.com.error.log
```

---

## 第七步：测试核心功能

### 7.1 测试用户注册

```bash
# 发送验证码
curl -X POST http://api.yuntucv.com/api/v1/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800000001"}'

# 注册用户
curl -X POST http://api.yuntucv.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username":"testuser",
    "phone":"13800000001",
    "verification_code":"123456",
    "password":"testpass123"
  }'
```

### 7.2 测试登录

```bash
curl -X POST http://api.yuntucv.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone":"13800000001",
    "password":"testpass123"
  }'
```

---

## 常用管理命令

### 重启服务

```bash
# 重启应用
systemctl restart yuntu-server

# 重载 Nginx
systemctl reload nginx

# 重启所有服务
systemctl restart yuntu-server nginx postgresql redis-server
```

### 查看状态

```bash
# 应用服务状态
systemctl status yuntu-server

# 所有服务状态
systemctl status nginx postgresql redis-server
```

### 查看日志

```bash
# 应用日志（最新 100 行）
tail -n 100 /var/www/api/logs/app.log

# 实时查看日志
tail -f /var/www/api/logs/app.log

# Systemd 日志
journalctl -u yuntu-server -n 100
```

### 更新代码

当需要更新代码时：

```bash
# 1. 在本地打包新版本
cd /Users/pretty/Documents/Workspace/YuntuServer
tar -czf yuntu-server-deploy.tar.gz app/ alembic/ requirements.txt alembic.ini
scp -P 777 yuntu-server-deploy.tar.gz root@59.110.51.85:/tmp/

# 2. 在服务器上备份并更新
ssh -p 777 root@59.110.51.85
cd /var/www/api
cp -r app app.backup.$(date +%Y%m%d)
tar -xzf /tmp/yuntu-server-deploy.tar.gz
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
systemctl restart yuntu-server
```

---

## 故障排查

### 问题 1: 服务启动失败

```bash
# 查看详细错误
journalctl -u yuntu-server -n 100 --no-pager

# 检查配置文件
cat /var/www/api/.env

# 手动启动测试
cd /var/www/api
source venv/bin/activate
gunicorn app.main:app --bind 127.0.0.1:8000
```

### 问题 2: 数据库连接失败

```bash
# 测试数据库连接
psql -U yuntu_user -d yuntu_production -h localhost

# 检查 PostgreSQL 状态
systemctl status postgresql

# 查看 PostgreSQL 日志
tail -f /var/log/postgresql/postgresql-14-main.log
```

### 问题 3: Nginx 502 错误

```bash
# 检查应用是否运行
systemctl status yuntu-server

# 检查端口监听
netstat -tlnp | grep 8000

# 查看 Nginx 错误日志
tail -f /var/log/nginx/error.log
```

---

## 完成！🎉

部署完成后，您的 YuntuServer 应该可以通过以下方式访问：

- **HTTP API**: http://api.yuntucv.com
- **API 文档**: http://api.yuntucv.com/docs
- **健康检查**: http://api.yuntucv.com/health

---

## 安全建议

1. **修改 root 密码**
   ```bash
   passwd
   ```

2. **配置 SSH 密钥认证**（禁用密码登录）

3. **定期备份数据库**
   ```bash
   pg_dump -U yuntu_user yuntu_production > backup_$(date +%Y%m%d).sql
   ```

4. **考虑申请 SSL 证书**（升级到 HTTPS）

5. **配置日志轮转**
   ```bash
   vim /etc/logrotate.d/yuntu-server
   ```

---

如有问题，请查看日志文件或参考 `DEPLOYMENT_HTTP.md` 文档。
