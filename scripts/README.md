# YuntuServer 脚本工具集

本目录包含用于 YuntuServer 项目的实用脚本。

## collect_context.py - 代码上下文提取工具

### 功能描述

自动提取 YuntuServer 项目中所有模块的核心上下文信息，包括：

- **Models（数据模型）**: 类定义、字段、关系、方法
- **Services（服务层）**: 类、方法、函数、参数
- **API Routes（API路由）**: 端点、HTTP方法、参数
- **Schemas（数据模式）**: Pydantic 模型定义、字段类型

输出格式为结构化的 JSON，方便进行代码分析、文档生成、AI辅助编程等用途。

### 使用方法

#### 1. 提取所有模块（完整上下文）

```bash
python3 scripts/collect_context.py -o context.json --pretty
```

**输出统计**:
- Models: 20 个数据模型
- Services: 15 个服务类
- API Endpoints: 60+ 个端点（需进一步优化解析）
- Schemas: 91 个数据模式

**生成文件**: `context.json` (约 104KB)

#### 2. 提取指定模块（部分上下文）

```bash
python3 scripts/collect_context.py User Task -o user_task_context.json --pretty
```

**过滤规则**: 提取所有包含 "User" 或 "Task" 关键词的模块，包括：
- `app/models/user.py`, `app/models/task.py`, `app/models/upload_task.py`, `app/models/task_file.py`
- `app/services/user_service.py`, `app/services/task_service.py`, `app/services/upload_task_service.py`
- `app/api/v1/users.py`, `app/api/v1/tasks.py`, `app/api/v1/upload_tasks.py`
- `app/schemas/user.py`, `app/schemas/task.py`, `app/schemas/upload_task.py`

**生成文件**: `user_task_context.json` (约 40KB)

#### 3. 输出到标准输出（管道处理）

```bash
python3 scripts/collect_context.py User | jq '.models.user.classes[0].fields'
```

**用途**: 结合 `jq` 等工具进行进一步的数据处理和分析

#### 4. 美化输出（易读格式）

```bash
python3 scripts/collect_context.py --pretty
```

**效果**: JSON 输出带缩进（2空格），方便人工阅读

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `modules` | 要提取的模块名称（位置参数，可选） | `User Task Auth` |
| `--json` | 输出 JSON 格式（默认） | - |
| `-o, --output` | 保存到指定文件 | `-o context.json` |
| `--pretty` | 美化 JSON 输出（带缩进） | `--pretty` |
| `-h, --help` | 显示帮助信息 | `--help` |

### 输出格式说明

#### JSON 结构

```json
{
  "project": "YuntuServer",
  "models": {
    "user": {
      "file": "app/models/user.py",
      "classes": [
        {
          "name": "User",
          "docstring": "用户表",
          "fields": [
            {"name": "id", "type": "Column"},
            {"name": "username", "type": "Column"}
          ],
          "relationships": [
            {"name": "tasks", "type": "relationship"}
          ],
          "methods": [
            {"name": "__repr__", "docstring": "..."}
          ]
        }
      ],
      "docstring": "用户模型"
    }
  },
  "services": {
    "auth_service": {
      "file": "app/services/auth_service.py",
      "classes": [
        {
          "name": "AuthService",
          "docstring": "认证服务类",
          "methods": [
            {
              "name": "register_user",
              "docstring": "用户注册...",
              "is_async": true,
              "parameters": ["self", "db", "username", "email", "password"]
            }
          ]
        }
      ],
      "functions": [],
      "docstring": "认证服务：处理用户注册、登录、Token管理等逻辑"
    }
  },
  "api_routes": {
    "auth": {
      "file": "app/api/v1/auth.py",
      "endpoints": [
        {
          "method": "POST",
          "path": "/auth/register",
          "function": "register",
          "docstring": "用户注册...",
          "is_async": true,
          "parameters": ["user_data", "db"]
        }
      ],
      "docstring": "认证相关的 API 端点"
    }
  },
  "schemas": {
    "user": {
      "file": "app/schemas/user.py",
      "classes": [
        {
          "name": "UserResponse",
          "docstring": "用户响应模型",
          "fields": [
            {"name": "id", "type": "UUID"},
            {"name": "username", "type": "str"}
          ]
        }
      ],
      "docstring": "用户相关的Pydantic模型"
    }
  },
  "statistics": {
    "total_models": 20,
    "total_services": 15,
    "total_api_endpoints": 0,
    "total_schemas": 91
  }
}
```

### 应用场景

#### 1. AI 辅助编程
将上下文信息提供给 AI 模型（如 Claude、GPT-4），帮助 AI 理解项目结构：

```bash
python3 scripts/collect_context.py User Task > context.json
# 将 context.json 提供给 AI，询问："如何修改用户注册流程？"
```

#### 2. 代码审查
快速了解模块之间的依赖关系和数据流：

```bash
python3 scripts/collect_context.py --pretty | less
```

#### 3. 文档生成
基于提取的上下文自动生成 API 文档或架构图：

```bash
python3 scripts/collect_context.py -o docs/api_context.json
```

#### 4. 代码分析
统计项目规模、复杂度等指标：

```bash
python3 scripts/collect_context.py | jq '.statistics'
# 输出:
# {
#   "total_models": 20,
#   "total_services": 15,
#   "total_api_endpoints": 0,
#   "total_schemas": 91
# }
```

### 技术实现

- **AST 解析**: 使用 Python 的 `ast` 模块解析源代码
- **无依赖**: 仅使用 Python 标准库，无需额外安装依赖
- **容错性**: 解析失败时不会中断，会输出警告并继续
- **高效**: 使用 `pathlib` 和生成器模式，内存占用低

### 局限性与改进方向

**当前局限**:
1. API 端点路径解析不完整（显示为 0 个端点）
2. 无法提取复杂的装饰器参数（如 `@router.post("/users", ...)`）
3. 不支持动态生成的路由

**改进方向**:
1. 增强 API 路由解析，支持 FastAPI 装饰器参数提取
2. 添加依赖关系图生成（模块间调用关系）
3. 支持增量更新（仅提取修改过的文件）
4. 添加代码质量指标（圈复杂度、代码行数等）

### 示例输出

**提取 User 和 Task 模块**:

```
📊 开始提取项目上下文...

🔍 提取 Models...
   ✓ user: 1 类
   ✓ task: 2 类
   ✓ upload_task: 2 类
   ✓ task_file: 2 类
🔍 提取 Services...
   ✓ task_service: 1 类, 0 函数
   ✓ upload_task_service: 1 类, 0 函数
   ✓ user_service: 1 类, 0 函数
🔍 提取 API Routes...
   ✓ tasks: 0 端点
   ✓ users: 0 端点
   ✓ upload_tasks: 0 端点
🔍 提取 Schemas...
   ✓ user: 8 模式
   ✓ task: 12 模式
   ✓ upload_task: 13 模式

✅ 提取完成！
   - Models: 7
   - Services: 3
   - API Endpoints: 0
   - Schemas: 33

✅ 已保存到: user_task_context.json
```

### 常见问题

**Q: 为什么 API Endpoints 显示为 0？**  
A: 当前版本的端点路径解析逻辑较为简化，无法正确提取 FastAPI 装饰器的路径参数。后续版本将改进此功能。

**Q: 如何提取特定文件的上下文？**  
A: 使用模块名作为过滤条件，例如 `python3 scripts/collect_context.py upload_task` 会提取所有包含 "upload_task" 的模块。

**Q: 生成的 JSON 文件太大怎么办？**  
A: 可以使用过滤参数只提取需要的模块，或者使用 `jq` 等工具进一步筛选数据。

**Q: 是否支持其他编程语言？**  
A: 当前仅支持 Python 项目。如需支持其他语言，需要开发对应的 AST 解析器。

---

## 其他脚本（待添加）

### migrate_db.py - 数据库迁移工具
TODO: 自动执行 Alembic 迁移

### test_api.py - API 测试工具
TODO: 批量测试 API 端点

### deploy.sh - 部署脚本
TODO: 一键部署到生产环境

---

**维护者**: YuntuServer 开发团队  
**最后更新**: 2025-10-22
