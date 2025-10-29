# YuntuServer HTTP 部署指南（无 SSL 证书）

本文档说明如何在没有 SSL 证书的情况下，使用 HTTP 协议部署 YuntuServer。

## ⚠️ 重要说明

- 此配置仅用于**测试环境**或**内网环境**
- **生产环境强烈建议使用 HTTPS**
- HTTP 传输不加密，存在安全风险

---

## 快速部署步骤

### 1️⃣ 服务器准备

```bash
# 登录服务器
ssh root@api.yuntucv.com

# 安装依赖（Ubuntu/Debian）
apt update && apt upgrade -y
apt install -y python3.10 python3.10-venv python3.10-dev \
    postgresql-14 postgresql-contrib-14 \
    redis-server \
    nginx

# 启动服务
systemctl start postgresql redis-server nginx
systemctl enable postgresql redis-server nginx
```

### 2️⃣ 配置数据库

```bash
# 创建 PostgreSQL 数据库
sudo -u postgres psql << EOF
CREATE DATABASE yuntu_production;
CREATE USER yuntu_user WITH ENCRYPTED PASSWORD 'YOUR_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE yuntu_production TO yuntu_user;
\c yuntu_production
GRANT ALL ON SCHEMA public TO yuntu_user;
EOF

# 配置 Redis 密码
echo "requirepass YOUR_REDIS_PASSWORD" >> /etc/redis/redis.conf
systemctl restart redis-server
```

### 3️⃣ 配置 Nginx（HTTP 版本）

在服务器上创建 Nginx 配置：

```bash
# 使用 HTTP 版本的配置文件
# 部署脚本会自动上传 deployment/nginx/api.yuntucv.com.http.conf

# 手动配置的话：
cp deployment/nginx/api.yuntucv.com.http.conf /etc/nginx/sites-available/api.yuntucv.com
ln -s /etc/nginx/sites-available/api.yuntucv.com /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 4️⃣ 本地配置环境变量

```bash
# 复制模板
cp .env.production.example .env.production

# 编辑配置（重要配置项）
vim .env.production
```

**HTTP 部署的关键配置**：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://yuntu_user:YOUR_DB_PASSWORD@localhost:5432/yuntu_production

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=YOUR_REDIS_PASSWORD

# JWT
SECRET_KEY=你的超级密钥（使用随机生成的64位字符串）

# 阿里云 OSS
OSS_ACCESS_KEY_ID=你的AccessKeyId
OSS_ACCESS_KEY_SECRET=你的AccessKeySecret
OSS_BUCKET_NAME=你的Bucket名称
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BASE_URL=https://你的Bucket名称.oss-cn-beijing.aliyuncs.com

# OSS 回调（使用 HTTP，不是 HTTPS！）
OSS_CALLBACK_URL=http://api.yuntucv.com/api/v1/oss-callback/upload-complete
OSS_CALLBACK_HOST=api.yuntucv.com

# CORS（允许 HTTP）
CORS_ORIGINS=["http://admin.yuntucv.com","http://www.yuntucv.com","http://localhost:3000"]

# 其他配置...
```

### 5️⃣ 执行部署

```bash
# 在本地项目目录执行
./deploy.sh
```

---

## 验证部署

```bash
# 测试 HTTP 接口
curl http://api.yuntucv.com/health

# 预期响应
{"status":"healthy","timestamp":"2025-10-25T..."}

# 浏览器访问 API 文档
http://api.yuntucv.com/docs

# 查看服务状态
ssh root@api.yuntucv.com "systemctl status yuntu-server"
```

---

## 与 HTTPS 部署的区别

| 项目 | HTTP 部署 | HTTPS 部署 |
|------|-----------|------------|
| Nginx 配置 | `api.yuntucv.com.http.conf` | `api.yuntucv.com.conf` |
| SSL 证书 | ❌ 不需要 | ✅ 需要 Let's Encrypt |
| OSS 回调 URL | `http://api.yuntucv.com/...` | `https://api.yuntucv.com/...` |
| CORS 配置 | 允许 `http://` 域名 | 允许 `https://` 域名 |
| 安全性 | ⚠️ 明文传输 | ✅ 加密传输 |
| 适用场景 | 测试/内网 | 生产环境 |

---

## 升级到 HTTPS

当您准备好 SSL 证书后，可以按以下步骤升级：

### 方案 A：使用 Let's Encrypt（免费）

```bash
# 1. 安装 Certbot
apt install -y certbot python3-certbot-nginx

# 2. 申请证书（自动配置 Nginx）
certbot --nginx -d api.yuntucv.com

# 3. 更新环境变量
vim /var/www/api/.env
# 修改: OSS_CALLBACK_URL=https://api.yuntucv.com/api/v1/oss-callback/upload-complete

# 4. 重启服务
systemctl restart yuntu-server

# 5. 测试 HTTPS
curl https://api.yuntucv.com/health
```

### 方案 B：手动替换配置文件

```bash
# 1. 替换 Nginx 配置为 HTTPS 版本
cp deployment/nginx/api.yuntucv.com.conf /etc/nginx/sites-available/api.yuntucv.com
nginx -t
systemctl reload nginx

# 2. 更新环境变量（同上）
```

---

## 常见问题

### Q1: OSS 回调失败

**可能原因**: OSS 回调 URL 使用了 `https://`，但服务器只配置了 HTTP

**解决方案**:
```bash
# 检查配置
grep OSS_CALLBACK /var/www/api/.env

# 应该是 http:// 而不是 https://
OSS_CALLBACK_URL=http://api.yuntucv.com/api/v1/oss-callback/upload-complete
```

### Q2: CORS 错误

**可能原因**: CORS 配置中使用了 `https://`，但前端使用 `http://`

**解决方案**:
```bash
# 更新 CORS 配置
CORS_ORIGINS=["http://admin.yuntucv.com","http://localhost:3000"]
```

### Q3: 微信登录失败

**说明**: 微信开放平台要求回调 URL 必须使用 HTTPS

**解决方案**: 微信登录功能必须升级到 HTTPS 才能使用

---

## 安全建议

即使使用 HTTP 部署，也应该：

1. **限制访问来源**
   ```bash
   # 在 Nginx 配置中添加 IP 白名单
   location / {
       allow 192.168.1.0/24;  # 允许内网
       allow YOUR_OFFICE_IP;   # 允许办公室 IP
       deny all;               # 拒绝其他

       proxy_pass http://127.0.0.1:8000;
   }
   ```

2. **配置防火墙**
   ```bash
   ufw allow from YOUR_IP to any port 80
   ufw deny 80
   ```

3. **定期备份数据**
   ```bash
   # 参考 docs/PRODUCTION_DEPLOYMENT.md 中的备份脚本
   ```

4. **尽快升级到 HTTPS**
   - 免费 SSL 证书：Let's Encrypt
   - 自动续期，无需手动维护

---

## 文件清单

- **Nginx HTTP 配置**: `deployment/nginx/api.yuntucv.com.http.conf`
- **Nginx HTTPS 配置**: `deployment/nginx/api.yuntucv.com.conf`
- **环境变量模板**: `.env.production.example`
- **部署脚本**: `deploy.sh`
- **Systemd 服务**: `deployment/systemd/yuntu-server.service`

---

## 总结

HTTP 部署适合：
- ✅ 开发测试环境
- ✅ 内网环境
- ✅ 快速验证功能

生产环境请使用 HTTPS：
- ✅ 数据加密传输
- ✅ 防止中间人攻击
- ✅ 微信登录等功能必需
- ✅ 提升用户信任度

**部署完成！** 🎉

访问地址：
- **API**: http://api.yuntucv.com
- **文档**: http://api.yuntucv.com/docs
- **健康检查**: http://api.yuntucv.com/health
