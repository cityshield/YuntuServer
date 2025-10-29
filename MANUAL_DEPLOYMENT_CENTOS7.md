# YuntuServer CentOS 7 部署完整步骤

## 服务器信息
- **操作系统**: CentOS Linux 7 (Core)
- **IP地址**: 59.110.51.85
- **SSH端口**: 777
- **用户**: root
- **部署目录**: /var/www/api/
- **域名**: api.yuntucv.com

---

## 第一步：本地打包项目（在 Mac 上执行）

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

# 上传到服务器
scp -P 777 yuntu-server-deploy.tar.gz root@59.110.51.85:/tmp/
```

---

## 第二步：服务器环境准备（CentOS 7）

### 2.1 更新系统

```bash
# 更新 yum 源
yum update -y

# 安装基础工具
yum install -y wget curl vim net-tools
```

### 2.2 安装 Python 3.10

CentOS 7 默认 Python 版本较低，需要从源码编译或使用 EPEL 仓库：

```bash
# 方法 1: 使用 IUS 仓库（推荐）
yum install -y https://repo.ius.io/ius-release-el7.rpm
yum install -y python310 python310-pip python310-devel

# 创建软链接
ln -s /usr/bin/python3.10 /usr/bin/python3
ln -s /usr/bin/pip3.10 /usr/bin/pip3

# 验证
python3 --version
# 应该显示 Python 3.10.x
```

**如果上述方法失败，使用方法 2（源码编译）**：

```bash
# 安装编译依赖
yum groupinstall -y "Development Tools"
yum install -y openssl-devel bzip2-devel libffi-devel zlib-devel

# 下载 Python 3.10
cd /tmp
wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz
tar -xzf Python-3.10.13.tgz
cd Python-3.10.13

# 编译安装
./configure --enable-optimizations --prefix=/usr/local
make altinstall

# 创建软链接
ln -s /usr/local/bin/python3.10 /usr/bin/python3
ln -s /usr/local/bin/pip3.10 /usr/bin/pip3

# 验证
python3 --version
```

### 2.3 安装 PostgreSQL 14

```bash
# 安装 PostgreSQL 14 仓库
yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 安装 PostgreSQL 14
yum install -y postgresql14-server postgresql14-contrib postgresql14-devel

# 初始化数据库
/usr/pgsql-14/bin/postgresql-14-setup initdb

# 启动并设置开机自启
systemctl start postgresql-14
systemctl enable postgresql-14

# 验证状态
systemctl status postgresql-14
```

### 2.4 配置 PostgreSQL

```bash
# 修改 PostgreSQL 配置允许密码认证
vim /var/lib/pgsql/14/data/pg_hba.conf

# 找到这几行：
# local   all             all                                     peer
# host    all             all             127.0.0.1/32            ident
# host    all             all             ::1/128                 ident

# 修改为：
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5
# host    all             all             ::1/128                 md5

# 重启 PostgreSQL
systemctl restart postgresql-14

# 创建数据库和用户
sudo -u postgres /usr/pgsql-14/bin/psql << 'EOF'
CREATE DATABASE yuntu_production;
CREATE USER yuntu_user WITH ENCRYPTED PASSWORD 'YuntuDB2025!@#';
GRANT ALL PRIVILEGES ON DATABASE yuntu_production TO yuntu_user;
\c yuntu_production
GRANT ALL ON SCHEMA public TO yuntu_user;
\q
EOF

# 测试连接
/usr/pgsql-14/bin/psql -U yuntu_user -d yuntu_production -h localhost -W
# 输入密码: YuntuDB2025!@#
# 成功后输入 \q 退出
```

### 2.5 安装 Redis

```bash
# 安装 EPEL 仓库
yum install -y epel-release

# 安装 Redis
yum install -y redis

# 配置 Redis 密码
echo "requirepass YuntuRedis2025!@#" >> /etc/redis.conf

# 启动并设置开机自启
systemctl start redis
systemctl enable redis

# 验证状态
systemctl status redis

# 测试连接
redis-cli
AUTH YuntuRedis2025!@#
PING
# 应该返回 PONG
exit
```

### 2.6 安装 Nginx

```bash
# 添加 Nginx 官方仓库
cat > /etc/yum.repos.d/nginx.repo << 'EOF'
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/$releasever/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://nginx.org/keys/nginx_signing.key
module_hotfixes=true
EOF

# 安装 Nginx
yum install -y nginx

# 启动并设置开机自启
systemctl start nginx
systemctl enable nginx

# 验证状态
systemctl status nginx
```

---

## 第三步：部署应用

### 3.1 创建部署目录

```bash
mkdir -p /var/www/api
cd /var/www/api

# 创建子目录
mkdir -p logs temp_uploads
```

### 3.2 解压项目文件

```bash
# 解压
tar -xzf /tmp/yuntu-server-deploy.tar.gz -C /var/www/api/

# 验证文件
ls -la
```

### 3.3 修改环境变量

```bash
vim /var/www/api/.env
```

**关键修改**：

```bash
# Database (PostgreSQL 14)
DATABASE_URL=postgresql+asyncpg://yuntu_user:YuntuDB2025!@#@localhost:5432/yuntu_production

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=YuntuRedis2025!@#

# 日志
LOG_FILE=/var/www/api/logs/app.log

# OSS 回调（HTTP）
OSS_CALLBACK_URL=http://api.yuntucv.com/api/v1/oss-callback/upload-complete
OSS_CALLBACK_HOST=api.yuntucv.com

# CORS
CORS_ORIGINS=["http://api.yuntucv.com","http://59.110.51.85"]
```

### 3.4 创建虚拟环境

```bash
cd /var/www/api

# 创建虚拟环境（使用 python3）
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 注意：如果安装 psycopg2-binary 失败，需要安装 PostgreSQL 开发包
# yum install -y postgresql14-devel
# 然后重新安装: pip install psycopg2-binary
```

### 3.5 运行数据库迁移

```bash
# 确保虚拟环境已激活
source /var/www/api/venv/bin/activate

# 运行迁移
alembic upgrade head
```

---

## 第四步：配置 Systemd 服务

### 4.1 创建服务文件

```bash
# 复制服务配置
cp /var/www/api/deployment/systemd/yuntu-server.service /etc/systemd/system/

# 编辑服务文件（CentOS 7 特定修改）
vim /etc/systemd/system/yuntu-server.service
```

**CentOS 7 版本的服务文件**：

```ini
[Unit]
Description=Yuntu Server - FastAPI Application
After=network.target postgresql-14.service redis.service
Wants=postgresql-14.service redis.service

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/var/www/api
Environment="PATH=/var/www/api/venv/bin"

ExecStart=/var/www/api/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 300 \
    --keep-alive 5 \
    --access-logfile /var/www/api/logs/access.log \
    --error-logfile /var/www/api/logs/error.log \
    --log-level info

Restart=always
RestartSec=10
StartLimitInterval=0

LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

### 4.2 启动服务

```bash
# 设置权限
chown -R root:root /var/www/api
chmod -R 755 /var/www/api
chmod -R 777 /var/www/api/logs
chmod -R 777 /var/www/api/temp_uploads

# 重载 systemd
systemctl daemon-reload

# 启动服务
systemctl start yuntu-server

# 查看状态
systemctl status yuntu-server

# 如果失败，查看日志
journalctl -u yuntu-server -n 50 --no-pager

# 设置开机自启
systemctl enable yuntu-server
```

### 4.3 验证服务

```bash
# 检查端口
netstat -tlnp | grep 8000

# 测试本地访问
curl http://127.0.0.1:8000/health
```

---

## 第五步：配置 Nginx

### 5.1 创建配置文件

CentOS 7 的 Nginx 配置目录结构不同：

```bash
# 创建配置文件
vim /etc/nginx/conf.d/api.yuntucv.com.conf
```

**配置内容**：

```nginx
server {
    listen 80;
    server_name api.yuntucv.com 59.110.51.85;

    access_log /var/log/nginx/api.yuntucv.com.access.log;
    error_log /var/log/nginx/api.yuntucv.com.error.log;

    client_max_body_size 1000M;
    client_body_timeout 300s;

    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # WebSocket 支持
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # API 路由
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        proxy_max_temp_file_size 1024m;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://127.0.0.1:8000;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

### 5.2 测试并重载 Nginx

```bash
# 测试配置
nginx -t

# 重载 Nginx
systemctl reload nginx

# 验证状态
systemctl status nginx
```

### 5.3 配置防火墙（CentOS 7 使用 firewalld）

```bash
# 启动 firewalld
systemctl start firewalld
systemctl enable firewalld

# 开放端口
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=777/tcp

# 重载防火墙
firewall-cmd --reload

# 查看开放端口
firewall-cmd --list-ports
```

### 5.4 关闭 SELinux（可选，避免权限问题）

```bash
# 临时关闭
setenforce 0

# 永久关闭
sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config

# 验证
getenforce
# 应该显示 Permissive 或 Disabled
```

---

## 第六步：验证部署

### 6.1 本地测试

```bash
# 在服务器上测试
curl http://127.0.0.1/health
curl http://localhost/health

# 应该返回 {"status":"healthy",...}
```

### 6.2 外部测试（在 Mac 上）

```bash
# 测试 IP 访问
curl http://59.110.51.85/health

# 测试域名访问
curl http://api.yuntucv.com/health
```

### 6.3 浏览器访问

- http://api.yuntucv.com/docs
- http://api.yuntucv.com/health
- http://59.110.51.85/docs

---

## 常用管理命令（CentOS 7）

### 查看服务状态

```bash
systemctl status yuntu-server
systemctl status nginx
systemctl status postgresql-14
systemctl status redis
```

### 重启服务

```bash
systemctl restart yuntu-server
systemctl restart nginx
```

### 查看日志

```bash
# 应用日志
tail -f /var/www/api/logs/app.log

# Systemd 日志
journalctl -u yuntu-server -f

# Nginx 日志
tail -f /var/log/nginx/api.yuntucv.com.access.log
tail -f /var/log/nginx/api.yuntucv.com.error.log
```

### 防火墙管理

```bash
# 查看防火墙状态
firewall-cmd --state

# 查看开放端口
firewall-cmd --list-all

# 开放新端口
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload
```

---

## 故障排查

### 问题 1: pip 安装依赖失败

```bash
# 安装编译工具
yum groupinstall -y "Development Tools"
yum install -y python3-devel postgresql14-devel

# 重新安装
pip install -r requirements.txt
```

### 问题 2: 无法连接数据库

```bash
# 检查 PostgreSQL 状态
systemctl status postgresql-14

# 查看日志
tail -f /var/lib/pgsql/14/data/log/postgresql-*.log

# 检查配置
vim /var/lib/pgsql/14/data/pg_hba.conf
```

### 问题 3: Nginx 无法访问

```bash
# 检查防火墙
firewall-cmd --list-ports

# 检查 SELinux
getenforce

# 关闭 SELinux
setenforce 0
```

---

## CentOS 7 特定注意事项

1. **使用 yum 而不是 apt**
2. **PostgreSQL 服务名是 postgresql-14**
3. **Nginx 配置在 /etc/nginx/conf.d/**
4. **防火墙使用 firewalld**
5. **需要关闭或配置 SELinux**
6. **Python 3.10 需要额外安装**

---

## 完成！🎉

部署完成后访问：
- http://api.yuntucv.com/docs
- http://api.yuntucv.com/health

如有问题，查看日志：
```bash
journalctl -u yuntu-server -n 100 --no-pager
tail -f /var/www/api/logs/app.log
```
