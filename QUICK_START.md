# ⚡ 快速启动指南

## 🚀 最快5分钟启动服务！

---

## 方式1：Docker一键部署（推荐）⭐

### 步骤1：配置环境变量（2分钟）

```bash
cd /Users/pretty/Documents/Workspace/YuntuServer
cp .env.example .env
```

**编辑 `.env` 文件，修改以下关键配置：**

```env
# JWT密钥（必须修改！）
SECRET_KEY=请替换为随机字符串

# 阿里云OSS（必须配置）
OSS_ACCESS_KEY_ID=你的AccessKey
OSS_ACCESS_KEY_SECRET=你的SecretKey
OSS_BUCKET_NAME=你的Bucket名称
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
```

**快速生成SECRET_KEY：**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 步骤2：一键部署（3分钟）

```bash
./scripts/deploy.sh
```

选择 **选项1 - 首次部署**

### 步骤3：验证部署

```bash
curl http://localhost/health
```

### 🎉 完成！访问：

- **API文档**: http://localhost/docs
- **WebSocket**: ws://localhost/ws
- **Flower监控**: http://localhost:5555

---

📖 **完整文档**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

🎉 **恭喜！服务已启动！**
