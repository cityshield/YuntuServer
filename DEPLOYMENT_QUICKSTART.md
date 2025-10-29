# YuntuServer 生产环境部署 - 快速开始

## 快速部署流程（5 步完成）

### 📋 前提条件

- ✅ 阿里云服务器（已解析域名 api.yuntucv.com）
- ✅ SSH 访问权限
- ✅ 服务器系统：Ubuntu 20.04/22.04 或 CentOS 7/8
- ✅ 阿里云 OSS、短信服务已开通

---

## 第一步：准备服务器环境

SSH 登录服务器，执行以下命令一键安装依赖：

```bash
# 登录服务器
ssh root@api.yuntucv.com

# 一键安装所有依赖（Ubuntu/Debian）
apt update && apt upgrade -y
apt install -y python3.10 python3.10-venv python3.10-dev \
    postgresql-14 postgresql-contrib-14 \
    redis-server \
    nginx \
    certbot python3-certbot-nginx

# 启动服务
systemctl start postgresql redis-server nginx
systemctl enable postgresql redis-server nginx
```

---

## 第二步：配置数据库和 Redis

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

---

## 第三步：配置 SSL 证书

```bash
# 申请 Let's Encrypt 证书
certbot --nginx -d api.yuntucv.com

# 按提示输入邮箱，同意条款，选择重定向 HTTP 到 HTTPS
```

---

## 第四步：本地配置环境变量

在本地项目目录执行：

```bash
# 1. 复制环境变量模板
cp .env.production.example .env.production

# 2. 编辑配置文件
vim .env.production
```

**必填配置项**：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://yuntu_user:YOUR_DB_PASSWORD@localhost:5432/yuntu_production

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=YOUR_REDIS_PASSWORD

# JWT 密钥（生成随机字符串）
SECRET_KEY=你的超级密钥_请使用随机生成的64位字符串

# 阿里云 OSS
OSS_ACCESS_KEY_ID=你的AccessKeyId
OSS_ACCESS_KEY_SECRET=你的AccessKeySecret
OSS_BUCKET_NAME=你的Bucket名称
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BASE_URL=https://你的Bucket名称.oss-cn-beijing.aliyuncs.com

# OSS 回调（重要！）
OSS_CALLBACK_URL=https://api.yuntucv.com/api/v1/oss-callback/upload-complete
OSS_CALLBACK_HOST=api.yuntucv.com

# 阿里云 STS
OSS_ROLE_ARN=acs:ram::你的账号ID:role/你的角色名

# 阿里云短信
SMS_SIGN_NAME=你的短信签名
SMS_TEMPLATE_CODE=你的短信模板CODE

# CORS（生产环境）
CORS_ORIGINS=["https://admin.yuntucv.com","https://www.yuntucv.com"]
```

---

## 第五步：一键部署

在本地项目目录执行：

```bash
# 确保脚本有执行权限
chmod +x deploy.sh

# 执行部署（会自动完成所有操作）
./deploy.sh
```

部署脚本会自动：
- ✅ 打包项目文件
- ✅ 上传到服务器
- ✅ 安装 Python 依赖
- ✅ 运行数据库迁移
- ✅ 配置 Systemd 服务
- ✅ 配置 Nginx 反向代理
- ✅ 启动应用服务
- ✅ 验证部署状态

---

## 验证部署

部署完成后，测试以下接口：

```bash
# 1. 健康检查
curl https://api.yuntucv.com/health
# 预期响应: {"status":"healthy",...}

# 2. API 文档
# 浏览器访问: https://api.yuntucv.com/docs

# 3. 查看服务状态
ssh root@api.yuntucv.com "systemctl status yuntu-server"

# 4. 查看实时日志
ssh root@api.yuntucv.com "tail -f /var/www/api/logs/app.log"
```

---

## 常用命令

### 更新部署

```bash
# 本地执行（自动备份并部署新版本）
./deploy.sh
```

### 查看日志

```bash
# 应用日志
ssh root@api.yuntucv.com "tail -f /var/www/api/logs/app.log"

# 系统日志
ssh root@api.yuntucv.com "journalctl -u yuntu-server -f"

# Nginx 日志
ssh root@api.yuntucv.com "tail -f /var/log/nginx/api.yuntucv.com.error.log"
```

### 重启服务

```bash
# 重启应用
ssh root@api.yuntucv.com "systemctl restart yuntu-server"

# 重载 Nginx
ssh root@api.yuntucv.com "systemctl reload nginx"
```

---

## 故障排查

### 问题 1: 部署脚本连接失败

```bash
# 检查 SSH 连接
ssh root@api.yuntucv.com

# 如果需要使用密钥
ssh -i ~/.ssh/your_key.pem root@api.yuntucv.com
```

### 问题 2: 服务启动失败

```bash
# 查看详细错误
ssh root@api.yuntucv.com "journalctl -u yuntu-server -n 50 --no-pager"

# 检查配置文件
ssh root@api.yuntucv.com "cat /var/www/api/.env"
```

### 问题 3: 502 错误

```bash
# 检查应用是否运行
ssh root@api.yuntucv.com "systemctl status yuntu-server"

# 检查端口监听
ssh root@api.yuntucv.com "netstat -tlnp | grep 8000"
```

---

## 下一步

部署成功后，您可以：

1. **配置自动备份**
   ```bash
   # 查看完整文档
   cat docs/PRODUCTION_DEPLOYMENT.md
   ```

2. **配置监控和告警**
   - 使用阿里云云监控
   - 配置服务异常告警

3. **性能优化**
   - 调整 Gunicorn workers 数量
   - 配置 Nginx 缓存
   - 优化数据库连接池

4. **安全加固**
   - 配置防火墙规则
   - 限制 SSH 访问
   - 定期更新系统

---

## 获取帮助

- 📖 **完整部署文档**: `docs/PRODUCTION_DEPLOYMENT.md`
- 📖 **OSS 回调配置**: `docs/OSS_CALLBACK_GUIDE.md`
- 🌐 **API 在线文档**: https://api.yuntucv.com/docs

---

**部署完成！** 🎉 您的 YuntuServer 已成功运行在生产环境！
