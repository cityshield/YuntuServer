# JWT Token 配置说明

## 当前配置（2025-10-22）

### Token 有效期

- **访问令牌 (Access Token)**: 43200 分钟 = **30天**
- **刷新令牌 (Refresh Token)**: 60 天

### 配置文件位置

`/app/config.py` 第 34-35 行：

```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30天 = 30 * 24 * 60 = 43200分钟
REFRESH_TOKEN_EXPIRE_DAYS: int = 60  # 刷新令牌延长到60天
```

### 用户体验

- ✅ 用户登录后可保持 **30天** 登录状态
- ✅ 不会频繁提示需要重新登录
- ✅ 只有在用户主动退出登录时才会清除登录状态
- ✅ LocalStorage 会保存用户信息和 token，浏览器关闭后重新打开仍然保持登录

### 前端 Token 管理

客户端通过 LocalStorage 保存：
- `token` - 访问令牌
- `refresh_token` - 刷新令牌
- `user` - 用户信息

#### Token 自动刷新机制

当访问令牌即将过期时，客户端应使用刷新令牌向 `/api/v1/auth/refresh` 发送请求获取新的访问令牌。

### 历史修改记录

| 日期 | 访问令牌有效期 | 刷新令牌有效期 | 原因 |
|------|--------------|--------------|------|
| 2025-10-22 之前 | 30分钟 | 7天 | 初始配置 |
| 2025-10-22 | **30天** | **60天** | 用户反馈登录提示过于频繁 |

### 安全建议

虽然延长了 token 有效期以提升用户体验，但仍需注意：

1. ✅ Token 存储在 LocalStorage（客户端应用）
2. ⚠️ 如发现账户异常，用户应主动退出登录并重新登录
3. ✅ 刷新令牌使用一次后会失效，需要获取新的刷新令牌
4. ✅ 后端仍然验证每个请求的 token 有效性

### API 端点

- `POST /api/v1/auth/login` - 登录，返回 access_token 和 refresh_token
- `POST /api/v1/auth/refresh` - 使用 refresh_token 获取新的 access_token
- `POST /api/v1/auth/logout` - 退出登录，撤销 refresh_token

### 相关文件

- `/app/config.py` - Token 有效期配置
- `/app/services/auth_service.py` - JWT token 生成和验证逻辑
- `/app/api/v1/auth.py` - 认证相关 API 端点
- （前端）`/src/stores/user.ts` - 用户状态管理
- （前端）`/src/api/auth.ts` - 认证 API 封装
