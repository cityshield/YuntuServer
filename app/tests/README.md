# YuntuServer API 测试文档

## 测试概述

本项目包含完整的API端点测试套件,覆盖所有核心功能。

### 测试统计
- **测试文件**: 4个
- **测试类**: 20+
- **测试用例**: 70+
- **覆盖模块**: 认证、用户、任务、文件

## 测试结构

```
app/tests/
├── __init__.py
├── conftest.py          # 测试配置和fixtures
├── test_auth.py         # 认证API测试
├── test_users.py        # 用户API测试
├── test_tasks.py        # 任务API测试
└── test_files.py        # 文件API测试
```

## 快速开始

### 1. 安装依赖

```bash
cd /Users/pretty/Documents/Workspace/YuntuServer
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 运行测试

**方式1: 使用测试脚本(推荐)**
```bash
./scripts/run_tests.sh
```

**方式2: 直接使用pytest**
```bash
# 运行所有测试
pytest app/tests/ -v

# 运行特定测试文件
pytest app/tests/test_auth.py -v

# 运行特定测试类
pytest app/tests/test_auth.py::TestAuthLogin -v

# 运行特定测试用例
pytest app/tests/test_auth.py::TestAuthLogin::test_login_with_username_success -v
```

### 3. 生成覆盖率报告

```bash
pytest app/tests/ --cov=app --cov-report=html --cov-report=term-missing
```

覆盖率报告会生成在 `htmlcov/index.html`

## 测试分类

### 使用标记筛选测试

```bash
# 只运行认证测试
pytest -m auth -v

# 只运行用户测试
pytest -m user -v

# 只运行任务测试
pytest -m task -v

# 只运行文件测试
pytest -m file -v

# 只运行API测试
pytest -m api -v
```

## 测试详情

### 1. 认证API测试 (test_auth.py)

#### TestAuthRegister - 注册测试
- ✅ `test_register_success` - 测试成功注册
- ✅ `test_register_duplicate_username` - 测试重复用户名
- ✅ `test_register_duplicate_email` - 测试重复邮箱
- ✅ `test_register_duplicate_phone` - 测试重复手机号
- ✅ `test_register_invalid_email` - 测试无效邮箱
- ✅ `test_register_short_password` - 测试密码太短

#### TestAuthLogin - 登录测试
- ✅ `test_login_with_username_success` - 使用用户名登录
- ✅ `test_login_with_email_success` - 使用邮箱登录
- ✅ `test_login_wrong_password` - 密码错误
- ✅ `test_login_nonexistent_user` - 不存在的用户
- ✅ `test_login_missing_fields` - 缺少字段

#### TestAuthRefresh - Token刷新测试
- ✅ `test_refresh_token_success` - 成功刷新Token
- ✅ `test_refresh_token_invalid` - 无效refresh_token

#### TestAuthLogout - 登出测试
- ✅ `test_logout_success` - 成功登出
- ✅ `test_logout_without_auth` - 未认证登出
- ✅ `test_logout_invalid_token` - 无效Token登出

#### TestAuthSendCode - 验证码测试
- ✅ `test_send_code_success` - 成功发送验证码
- ✅ `test_send_code_invalid_phone` - 无效手机号

### 2. 用户API测试 (test_users.py)

#### TestUserInfo - 用户信息测试
- ✅ `test_get_current_user` - 获取当前用户信息
- ✅ `test_get_current_user_without_auth` - 未认证获取用户信息
- ✅ `test_get_current_user_invalid_token` - 无效Token
- ✅ `test_update_user_profile` - 更新用户资料
- ✅ `test_update_user_email` - 更新邮箱
- ✅ `test_update_user_duplicate_email` - 更新为已存在的邮箱

#### TestUserBalance - 余额测试
- ✅ `test_get_balance` - 获取余额
- ✅ `test_recharge` - 充值
- ✅ `test_recharge_invalid_amount` - 无效充值金额
- ✅ `test_recharge_too_large` - 充值金额过大

#### TestUserTransactions - 交易记录测试
- ✅ `test_get_transactions_empty` - 获取空交易记录
- ✅ `test_get_transactions_after_recharge` - 充值后的交易记录
- ✅ `test_get_transactions_pagination` - 交易记录分页
- ✅ `test_get_transactions_filter_by_type` - 按类型筛选

#### TestUserBills - 账单测试
- ✅ `test_get_bills_empty` - 获取空账单
- ✅ `test_get_bills_pagination` - 账单分页

### 3. 任务API测试 (test_tasks.py)

#### TestTaskCreate - 任务创建测试
- ✅ `test_create_task_success` - 成功创建任务
- ✅ `test_create_task_without_auth` - 未认证创建任务
- ✅ `test_create_task_insufficient_balance` - 余额不足
- ✅ `test_create_task_invalid_frame_range` - 无效帧范围
- ✅ `test_create_task_missing_required_fields` - 缺少必填字段

#### TestTaskList - 任务列表测试
- ✅ `test_get_tasks_list` - 获取任务列表
- ✅ `test_get_tasks_empty` - 获取空任务列表
- ✅ `test_get_tasks_pagination` - 任务列表分页
- ✅ `test_get_tasks_filter_by_status` - 按状态筛选

#### TestTaskDetail - 任务详情测试
- ✅ `test_get_task_detail` - 获取任务详情
- ✅ `test_get_task_not_found` - 获取不存在的任务
- ✅ `test_get_other_user_task` - 获取其他用户的任务

#### TestTaskControl - 任务控制测试
- ✅ `test_pause_task` - 暂停任务
- ✅ `test_resume_task` - 恢复任务
- ✅ `test_cancel_task` - 取消任务
- ✅ `test_delete_task` - 删除任务

#### TestTaskLogs - 任务日志测试
- ✅ `test_get_task_logs` - 获取任务日志
- ✅ `test_get_task_logs_pagination` - 任务日志分页

### 4. 文件API测试 (test_files.py)

#### TestFileUpload - 文件上传测试
- ✅ `test_upload_file_success` - 成功上传文件
- ✅ `test_upload_file_without_auth` - 未认证上传
- ✅ `test_upload_large_file` - 上传大文件
- ✅ `test_upload_invalid_file_type` - 无效文件类型
- ✅ `test_upload_empty_file` - 上传空文件
- ✅ `test_upload_maya_scene_files` - 上传Maya场景文件

#### TestFileDownload - 文件下载测试
- ✅ `test_get_download_url` - 获取下载URL
- ✅ `test_download_nonexistent_file` - 下载不存在的文件
- ✅ `test_download_without_auth` - 未认证下载

#### TestFileList - 文件列表测试
- ✅ `test_list_user_files` - 获取用户文件列表
- ✅ `test_list_files_pagination` - 文件列表分页

#### TestFileDelete - 文件删除测试
- ✅ `test_delete_file_success` - 成功删除文件
- ✅ `test_delete_nonexistent_file` - 删除不存在的文件
- ✅ `test_delete_file_without_auth` - 未认证删除

## Fixtures

### 数据库Fixtures
- `db_session` - 测试数据库会话
- `test_user` - 测试用户1
- `test_user2` - 测试用户2

### 认证Fixtures
- `auth_headers` - 用户1的认证头
- `auth_headers2` - 用户2的认证头

### 客户端Fixtures
- `client` - 测试HTTP客户端

### 数据生成Fixtures
- `fake_user_data` - 生成假用户数据
- `fake_task_data` - 生成假任务数据

## 测试配置

### pytest.ini
- 自动发现测试文件
- 测试标记定义
- 覆盖率配置
- 日志配置

### conftest.py
- 数据库会话管理
- 测试用户创建
- 认证Token获取
- 测试数据生成

## 最佳实践

1. **隔离性**: 每个测试用例独立,不依赖其他测试
2. **清理**: 测试后自动清理数据
3. **可重复**: 测试结果一致,可重复执行
4. **有意义**: 测试名称清晰,描述测试意图
5. **覆盖全面**: 覆盖正常流程和异常情况

## 常见问题

### Q: 测试数据库在哪里?
A: 使用SQLite内存数据库 `test.db`,每次测试后自动清理

### Q: 如何跳过某个测试?
A: 使用 `@pytest.mark.skip` 装饰器

### Q: 如何只运行失败的测试?
A: `pytest --lf` (last-failed)

### Q: 如何调试测试?
A: `pytest -s -v` (-s显示print输出)

### Q: 如何并行运行测试?
A: 安装 `pytest-xdist` 后运行 `pytest -n auto`

## 贡献指南

添加新测试时:
1. 在相应的测试文件中添加测试类和方法
2. 使用清晰的测试名称
3. 添加docstring说明测试目的
4. 使用适当的pytest标记
5. 确保测试独立可运行

## 联系方式

项目路径: `/Users/pretty/Documents/Workspace/YuntuServer`
测试目录: `/Users/pretty/Documents/Workspace/YuntuServer/app/tests`
