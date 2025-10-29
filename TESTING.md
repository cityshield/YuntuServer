# YuntuServer API 测试文档

## 快速开始

### 运行测试

```bash
# 方式1: 使用脚本(推荐)
./scripts/run_tests.sh

# 方式2: 直接使用pytest
pytest app/tests/ -v

# 方式3: 生成覆盖率报告
pytest app/tests/ --cov=app --cov-report=html
```

## 测试覆盖

### 测试统计
- **测试文件**: 4个
- **测试用例**: 70+
- **覆盖模块**: 认证、用户、任务、文件

### 测试文件
```
app/tests/
├── conftest.py          # 测试配置和fixtures
├── test_auth.py         # 认证API测试 (20+用例)
├── test_users.py        # 用户API测试 (20+用例)
├── test_tasks.py        # 任务API测试 (20+用例)
└── test_files.py        # 文件API测试 (15+用例)
```

## 测试分类

### 按标记运行测试

```bash
# 认证测试
pytest -m auth -v

# 用户测试
pytest -m user -v

# 任务测试
pytest -m task -v

# 文件测试
pytest -m file -v

# API测试
pytest -m api -v
```

## 测试内容

### 1. 认证API (/api/v1/auth)
- ✅ 用户注册 (成功/失败场景)
- ✅ 用户登录 (用户名/邮箱)
- ✅ Token刷新
- ✅ 用户登出
- ✅ 发送验证码

### 2. 用户API (/api/v1/users)
- ✅ 获取用户信息
- ✅ 更新用户资料
- ✅ 余额查询
- ✅ 账户充值
- ✅ 交易记录
- ✅ 账单记录

### 3. 任务API (/api/v1/tasks)
- ✅ 创建任务
- ✅ 任务列表(分页/筛选)
- ✅ 任务详情
- ✅ 暂停/恢复/取消任务
- ✅ 删除任务
- ✅ 任务日志

### 4. 文件API (/api/v1/files)
- ✅ 文件上传
- ✅ 文件下载
- ✅ 文件列表
- ✅ 文件删除

## 测试特性

### Fixtures
- `db_session` - 测试数据库会话
- `client` - HTTP测试客户端
- `test_user` / `test_user2` - 测试用户
- `auth_headers` - 认证头
- `fake_user_data` - 假用户数据
- `fake_task_data` - 假任务数据

### 配置
- 使用SQLite测试数据库
- 自动清理测试数据
- 异步测试支持
- 覆盖率报告

## 测试命令

```bash
# 运行所有测试
pytest app/tests/ -v

# 运行特定文件
pytest app/tests/test_auth.py -v

# 运行特定测试类
pytest app/tests/test_auth.py::TestAuthLogin -v

# 运行特定测试用例
pytest app/tests/test_auth.py::TestAuthLogin::test_login_with_username_success -v

# 运行失败的测试
pytest --lf -v

# 显示详细输出
pytest -s -v

# 生成HTML覆盖率报告
pytest --cov=app --cov-report=html
```

## 测试覆盖率

运行测试后查看覆盖率报告:

```bash
# 终端查看
pytest --cov=app --cov-report=term-missing

# HTML报告(推荐)
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 文档

详细测试文档: [app/tests/README.md](app/tests/README.md)

## 下一步

1. 持续添加新的测试用例
2. 提高测试覆盖率至90%+
3. 添加集成测试
4. 添加性能测试
5. 配置CI/CD自动测试
