# API 测试脚本目录

这个目录包含了各个功能模块的本地测试脚本，用于快速验证 API 功能。

## 📁 目录结构

```
scripts/api_tests/
├── README.md              # 本文档
├── test_template.py       # 测试脚本模板
├── test_auth.py          # 认证相关测试（登录、注册、验证码）
├── test_tasks.py         # 任务相关测试
├── test_users.py         # 用户相关测试
└── test_files.py         # 文件上传相关测试
```

## 🎯 使用方法

### 1. 确保服务器运行

```bash
# 在项目根目录
source venv/bin/activate
uvicorn app.main:app --reload
```

### 2. 运行测试脚本

```bash
# 在项目根目录
python scripts/api_tests/test_auth.py
```

## 📝 测试脚本规范

每个测试脚本应该：

1. **从环境变量读取配置**：避免硬编码敏感信息
2. **提供清晰的输出**：使用emoji和格式化输出
3. **包含错误处理**：捕获并显示详细错误信息
4. **支持交互输入**：允许用户输入测试数据
5. **独立运行**：不依赖其他测试脚本

## 🔧 环境变量

测试脚本从 `.env` 文件读取配置，主要包括：

- `OSS_ACCESS_KEY_ID`: 阿里云访问密钥ID
- `OSS_ACCESS_KEY_SECRET`: 阿里云访问密钥Secret
- `SMS_SIGN_NAME`: 短信签名
- `SMS_TEMPLATE_CODE`: 短信模板代码
- `DATABASE_URL`: 数据库连接URL
- `SECRET_KEY`: JWT密钥

## 📋 测试脚本示例

参考 `test_template.py` 了解如何编写新的测试脚本。

## ⚠️ 注意事项

1. **不要提交包含密钥的文件**：所有配置从 `.env` 读取
2. **测试前检查环境**：确保数据库和必要的服务已启动
3. **使用测试数据**：避免影响生产数据
4. **清理测试数据**：测试完成后清理创建的测试数据

## 🧪 测试类型

### 单元测试
使用 pytest 框架，位于 `app/tests/` 目录

### 集成测试
位于当前目录，测试完整的 API 流程

### 性能测试
使用 locust 或其他性能测试工具

## 📚 相关文档

- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest 文档](https://docs.pytest.org/)
- [项目 API 文档](http://localhost:8000/docs)
