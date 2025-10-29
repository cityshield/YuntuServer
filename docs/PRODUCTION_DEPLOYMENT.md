# YuntuServer 生产环境部署指南

## 概述

本文档详细说明如何将 YuntuServer 部署到阿里云服务器（api.yuntucv.com）的 `/var/www/api/` 目录。

---

## 架构说明

### 技术栈

- **应用服务器**: Gunicorn + Uvicorn Workers (FastAPI)
- **反向代理**: Nginx
- **进程管理**: Systemd
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 7+
- **SSL证书**: Let's Encrypt
- **任务队列**: Celery + Redis

### 部署架构

```
Internet
    ↓
Nginx (443/80)
    ↓
Gunicorn (127.0.0.1:8000)
    ↓
FastAPI Application
    ↓
PostgreSQL + Redis
```

---

## 一、服务器准备

### 1.1 服务器要求

- **操作系统**: Ubuntu 20.04/22.04 LTS 或 CentOS 7/8
- **最低配置**: 2 核 CPU, 4GB RAM, 40GB 硬盘
- **推荐配置**: 4 核 CPU, 8GB RAM, 100GB 硬盘
- **公网 IP**: 已绑定域名 api.yuntucv.com

### 1.2 SSH 登录服务器

```bash
ssh root@api.yuntucv.com
```

### 1.3 更新系统

```bash
# Ubuntu/Debian
apt update && apt upgrade -y

# CentOS/RHEL
yum update -y
```

---

## 二、安装依赖软件

### 2.1 安装 Python 3.10+

```bash
# Ubuntu 22.04 自带 Python 3.10
python3 --version

# 如果版本过低，安装 Python 3.10
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.10 python3.10-venv python3.10-dev
```

### 2.2 安装 PostgreSQL 14

```bash
# Ubuntu
apt install -y postgresql-14 postgresql-contrib-14

# 启动并设置开机自启
systemctl start postgresql
systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE yuntu_production;
CREATE USER yuntu_user WITH ENCRYPTED PASSWORD 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE yuntu_production TO yuntu_user;
\c yuntu_production
GRANT ALL ON SCHEMA public TO yuntu_user;
EOF
```

### 2.3 安装 Redis

```bash
# Ubuntu
apt install -y redis-server

# 配置 Redis 密码
sed -i 's/# requirepass foobared/requirepass YOUR_REDIS_PASSWORD/' /etc/redis/redis.conf

# 重启 Redis
systemctl restart redis-server
systemctl enable redis-server

# 测试连接
redis-cli
AUTH YOUR_REDIS_PASSWORD
PING
```

### 2.4 安装 Nginx

```bash
# Ubuntu
apt install -y nginx

# 启动并设置开机自启
systemctl start nginx
systemctl enable nginx
```

### 2.5 安装 Certbot (SSL 证书)

```bash
# Ubuntu
apt install -y certbot python3-certbot-nginx
```

---

## 三、配置 SSL 证书

### 3.1 申请 Let's Encrypt 证书

```bash
# 确保域名已解析到服务器
certbot --nginx -d api.yuntucv.com

# 按照提示输入邮箱，同意条款
# 选择是否重定向 HTTP 到 HTTPS（推荐选择 Yes）
```

### 3.2 自动续期

```bash
# 测试自动续期
certbot renew --dry-run

# Cron 任务已自动添加，无需手动配置
```

---

## 四、部署应用

### 4.1 创建部署目录

```bash
# 创建目录
mkdir -p /var/www/api
cd /var/www/api

# 创建日志目录
mkdir -p /var/www/api/logs
```

### 4.2 配置环境变量

在本地创建 `.env.production` 文件：

```bash
# 复制模板
cp .env.production.example .env.production

# 编辑配置文件，填入真实值
vim .env.production
```

**重要配置项**:

- `DATABASE_URL`: PostgreSQL 连接字符串
- `REDIS_URL` + `REDIS_PASSWORD`: Redis 连接信息
- `SECRET_KEY`: JWT 密钥（使用强随机字符串）
- `OSS_*`: 阿里云 OSS 配置
- `SMS_*`: 阿里云短信配置
- `WECHAT_*`: 微信登录配置（如需要）
- `OSS_CALLBACK_URL`: 设置为 `https://api.yuntucv.com/api/v1/oss-callback/upload-complete`
- `OSS_CALLBACK_HOST`: 设置为 `api.yuntucv.com`

### 4.3 运行部署脚本

在本地项目目录执行：

```bash
# 确保部署脚本有执行权限
chmod +x deploy.sh

# 执行部署
./deploy.sh
```

部署脚本会自动执行以下操作：

1. ✅ 检查必要文件
2. ✅ 打包项目文件
3. ✅ 上传到服务器
4. ✅ 备份当前版本（如果存在）
5. ✅ 解压新版本
6. ✅ 安装 Python 依赖
7. ✅ 运行数据库迁移
8. ✅ 重启服务
9. ✅ 验证服务状态

---

## 五、手动部署步骤（可选）

如果不使用自动部署脚本，可以按以下步骤手动部署：

### 5.1 配置 Systemd 服务

```bash
# 复制服务配置文件
cp deployment/systemd/yuntu-server.service /etc/systemd/system/

# 重载 systemd
systemctl daemon-reload

# 启动服务
systemctl start yuntu-server

# 设置开机自启
systemctl enable yuntu-server

# 查看状态
systemctl status yuntu-server
```

### 5.2 配置 Nginx

```bash
# 复制 Nginx 配置
cp deployment/nginx/api.yuntucv.com.conf /etc/nginx/sites-available/

# 创建软链接
ln -s /etc/nginx/sites-available/api.yuntucv.com /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重载 Nginx
systemctl reload nginx
```

### 5.3 配置 Celery Worker（可选）

如果需要后台任务处理：

```bash
# 创建 Celery 服务配置
cat > /etc/systemd/system/yuntu-celery.service << 'EOF'
[Unit]
Description=Yuntu Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/api
Environment="PATH=/var/www/api/venv/bin"
ExecStart=/var/www/api/venv/bin/celery -A app.celery worker --loglevel=info --logfile=/var/www/api/logs/celery.log

Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动 Celery
systemctl daemon-reload
systemctl start yuntu-celery
systemctl enable yuntu-celery
```

---

## 六、验证部署

### 6.1 检查服务状态

```bash
# 检查应用服务
systemctl status yuntu-server

# 检查 Nginx
systemctl status nginx

# 检查日志
tail -f /var/www/api/logs/app.log
tail -f /var/log/nginx/api.yuntucv.com.access.log
tail -f /var/log/nginx/api.yuntucv.com.error.log
```

### 6.2 测试 API 接口

```bash
# 健康检查
curl https://api.yuntucv.com/health

# 预期响应：
# {"status":"healthy","timestamp":"2025-10-25T..."}

# API 文档
curl https://api.yuntucv.com/docs
# 浏览器访问: https://api.yuntucv.com/docs
```

### 6.3 测试 WebSocket

```bash
# 使用 wscat 测试（需先安装: npm install -g wscat）
wscat -c wss://api.yuntucv.com/ws
```

---

## 七、监控和维护

### 7.1 查看日志

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

### 7.2 重启服务

```bash
# 重启应用
systemctl restart yuntu-server

# 重载 Nginx（不中断连接）
systemctl reload nginx

# 重启 Nginx
systemctl restart nginx
```

### 7.3 更新部署

```bash
# 在本地项目目录执行
./deploy.sh

# 脚本会自动备份当前版本，部署新版本，并重启服务
```

### 7.4 回滚到之前版本

```bash
# SSH 登录服务器
ssh root@api.yuntucv.com

# 查看备份
ls -la /var/www/api/backup-*

# 回滚（假设要回滚到 backup-20251025-120000）
cd /var/www/api
rm -rf app alembic requirements.txt alembic.ini
cp -r backup-20251025-120000/* .

# 重启服务
systemctl restart yuntu-server
```

---

## 八、性能优化

### 8.1 调整 Gunicorn Workers

根据 CPU 核心数调整 workers 数量：

```bash
# 编辑 systemd 服务配置
vim /etc/systemd/system/yuntu-server.service

# 修改 --workers 参数
# 推荐值: (2 × CPU核心数) + 1
# 例如 4 核 CPU: --workers 9

# 重载并重启
systemctl daemon-reload
systemctl restart yuntu-server
```

### 8.2 启用 Nginx 缓存

```bash
# 在 Nginx 配置中添加缓存
vim /etc/nginx/sites-available/api.yuntucv.com

# 在 http 块中添加：
# proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m;

# 在 location / 中添加：
# proxy_cache api_cache;
# proxy_cache_valid 200 5m;
# proxy_cache_key "$scheme$request_method$host$request_uri";
```

### 8.3 配置 PostgreSQL

```bash
# 优化 PostgreSQL 配置
vim /etc/postgresql/14/main/postgresql.conf

# 调整参数（根据服务器配置）
# shared_buffers = 256MB
# effective_cache_size = 1GB
# maintenance_work_mem = 64MB
# checkpoint_completion_target = 0.9
# max_connections = 100

# 重启 PostgreSQL
systemctl restart postgresql
```

---

## 九、安全加固

### 9.1 配置防火墙

```bash
# Ubuntu (UFW)
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

### 9.2 限制 SSH 访问

```bash
# 只允许密钥登录
vim /etc/ssh/sshd_config
# 设置: PasswordAuthentication no

# 重启 SSH
systemctl restart sshd
```

### 9.3 配置自动备份

```bash
# 创建备份脚本
cat > /root/backup-yuntu.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p ${BACKUP_DIR}

# 备份数据库
PGPASSWORD='YOUR_DB_PASSWORD' pg_dump -U yuntu_user yuntu_production > ${BACKUP_DIR}/db-${DATE}.sql

# 备份应用文件
tar -czf ${BACKUP_DIR}/app-${DATE}.tar.gz -C /var/www/api .

# 保留最近 7 天的备份
find ${BACKUP_DIR} -name "*.sql" -mtime +7 -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: ${DATE}"
EOF

chmod +x /root/backup-yuntu.sh

# 添加 Cron 任务（每天凌晨 2 点备份）
crontab -e
# 添加: 0 2 * * * /root/backup-yuntu.sh >> /var/log/backup.log 2>&1
```

---

## 十、故障排查

### 10.1 服务无法启动

```bash
# 查看详细日志
journalctl -u yuntu-server -n 100 --no-pager

# 检查配置文件
cat /var/www/api/.env

# 检查数据库连接
psql -U yuntu_user -d yuntu_production -h localhost

# 检查 Redis 连接
redis-cli -a YOUR_REDIS_PASSWORD PING
```

### 10.2 502 Bad Gateway

```bash
# 检查应用是否运行
systemctl status yuntu-server

# 检查端口监听
netstat -tlnp | grep 8000

# 查看 Nginx 错误日志
tail -f /var/log/nginx/error.log
```

### 10.3 数据库连接失败

```bash
# 检查 PostgreSQL 状态
systemctl status postgresql

# 检查连接配置
vim /var/www/api/.env
# 确认 DATABASE_URL 格式正确

# 测试连接
psql postgresql://yuntu_user:PASSWORD@localhost:5432/yuntu_production
```

### 10.4 OSS 回调失败

```bash
# 检查回调配置
grep OSS_CALLBACK /var/www/api/.env

# 应该是:
# OSS_CALLBACK_URL=https://api.yuntucv.com/api/v1/oss-callback/upload-complete
# OSS_CALLBACK_HOST=api.yuntucv.com

# 测试回调接口
curl -X POST https://api.yuntucv.com/api/v1/oss-callback/upload-complete

# 查看回调日志
grep "OSS callback" /var/www/api/logs/app.log
```

---

## 十一、常用命令速查

```bash
# 部署相关
./deploy.sh                                    # 部署新版本
ssh root@api.yuntucv.com                       # 登录服务器

# 服务管理
systemctl start yuntu-server                   # 启动服务
systemctl stop yuntu-server                    # 停止服务
systemctl restart yuntu-server                 # 重启服务
systemctl status yuntu-server                  # 查看状态
systemctl enable yuntu-server                  # 开机自启

# 日志查看
tail -f /var/www/api/logs/app.log             # 应用日志
journalctl -u yuntu-server -f                  # Systemd 日志
tail -f /var/log/nginx/api.yuntucv.com.access.log  # Nginx 访问日志
tail -f /var/log/nginx/api.yuntucv.com.error.log   # Nginx 错误日志

# Nginx 管理
nginx -t                                       # 测试配置
systemctl reload nginx                         # 重载配置
systemctl restart nginx                        # 重启 Nginx

# 数据库管理
sudo -u postgres psql yuntu_production         # 进入数据库
cd /var/www/api && source venv/bin/activate && alembic upgrade head  # 运行迁移

# 进程监控
ps aux | grep gunicorn                         # 查看进程
netstat -tlnp | grep 8000                      # 查看端口
top                                            # 系统资源监控
htop                                           # 更好的监控工具
```

---

## 十二、联系支持

如遇到问题，请检查：

1. 📋 日志文件: `/var/www/api/logs/app.log`
2. 📋 Systemd 日志: `journalctl -u yuntu-server`
3. 📋 Nginx 日志: `/var/log/nginx/api.yuntucv.com.error.log`
4. 📖 项目文档: `/var/www/api/docs/`

---

## 附录

### A. 目录结构

```
/var/www/api/
├── app/                    # 应用代码
├── alembic/                # 数据库迁移
├── scripts/                # 辅助脚本
├── logs/                   # 日志文件
├── temp_uploads/           # 临时上传目录
├── venv/                   # Python 虚拟环境
├── .env                    # 环境配置
├── requirements.txt        # Python 依赖
├── alembic.ini            # Alembic 配置
└── backup-*/              # 备份目录
```

### B. 端口说明

- **80**: HTTP (自动重定向到 HTTPS)
- **443**: HTTPS (Nginx)
- **8000**: 应用服务 (Gunicorn, 仅本地访问)
- **5432**: PostgreSQL (仅本地访问)
- **6379**: Redis (仅本地访问)

### C. 相关文档

- [OSS 回调配置指南](./OSS_CALLBACK_GUIDE.md)
- [API 使用文档](https://api.yuntucv.com/docs)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Nginx 官方文档](https://nginx.org/en/docs/)
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)

---

**部署完成！** 🎉

您的 YuntuServer 已成功部署到生产环境：

- **API 地址**: https://api.yuntucv.com
- **API 文档**: https://api.yuntucv.com/docs
- **健康检查**: https://api.yuntucv.com/health
