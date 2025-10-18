# 阿里云 RAM 角色配置指南

## 📋 配置步骤

### 步骤 1：登录阿里云控制台

访问：https://ram.console.aliyun.com/

### 步骤 2：创建 RAM 角色

1. 点击左侧菜单 **"RAM角色管理"**
2. 点击 **"创建RAM角色"**
3. 选择可信实体类型：**"阿里云账号"**
4. 点击 **"下一步"**

### 步骤 3：填写角色信息

| 字段 | 值 | 说明 |
|------|-----|------|
| **角色名称** | `ossuploadrole` | 用于 STS 临时授权的角色名 |
| **备注** | OSS 文件上传专用角色 | 可选，便于管理 |
| **选择云账号** | **当前云账号** | 允许当前账号下的资源使用此角色 |

点击 **"完成"**

### 步骤 4：为角色添加权限策略

1. 在角色列表中找到刚创建的 `ossuploadrole`
2. 点击角色名称进入详情页
3. 点击 **"添加权限"** 按钮
4. 选择权限策略：

#### 方案 A：使用系统策略（推荐，快速配置）

搜索并选择：**`AliyunOSSFullAccess`**

✅ **优点**：配置简单，权限完整
⚠️ **注意**：权限较大，包含所有 OSS 操作

#### 方案 B：自定义权限策略（推荐，生产环境）

创建自定义策略，限制只能上传到特定 Bucket：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject",
        "oss:InitiateMultipartUpload",
        "oss:UploadPart",
        "oss:UploadPartCopy",
        "oss:CompleteMultipartUpload",
        "oss:AbortMultipartUpload",
        "oss:ListParts"
      ],
      "Resource": [
        "acs:oss:*:*:yuntu-render",
        "acs:oss:*:*:yuntu-render/*"
      ]
    }
  ]
}
```

将 `yuntu-render` 替换为您的 Bucket 名称。

**配置步骤**：
1. 访问：https://ram.console.aliyun.com/policies
2. 点击 **"创建权限策略"**
3. 策略名称：`OSSUploadPolicy`
4. 配置模式：**脚本配置**
5. 粘贴上述 JSON
6. 点击 **"确定"**
7. 返回角色管理，为 `ossuploadrole` 添加此策略

### 步骤 5：获取角色 ARN

1. 在角色详情页，找到 **"基本信息"** 区域
2. 复制 **ARN** 字段的值，格式如下：

```
acs:ram::1234567890123456:role/ossuploadrole
```

其中 `1234567890123456` 是您的阿里云账号 ID。

### 步骤 6：配置到环境变量

#### 方式 1：使用 `.env` 文件（推荐）

在 `YuntuServer/.env` 文件中添加：

```bash
# STS 配置
OSS_ROLE_ARN=acs:ram::1234567890123456:role/ossuploadrole
STS_ENDPOINT=sts.cn-beijing.aliyuncs.com
```

#### 方式 2：使用 `config.ini`

在 `YuntuServer/config.ini` 中添加：

```ini
[OSS]
RoleARN=acs:ram::1234567890123456:role/ossuploadrole
STSEndpoint=sts.cn-beijing.aliyuncs.com
```

### 步骤 7：验证配置

运行以下 Python 脚本测试：

```python
from app.services.sts_service import sts_service

try:
    credentials = sts_service.get_upload_credentials(
        user_id=1,
        task_id="test_123",
        duration_seconds=3600
    )
    print("✅ STS 凭证获取成功:")
    print(f"  AccessKeyId: {credentials['accessKeyId'][:20]}...")
    print(f"  SecurityToken: {credentials['securityToken'][:50]}...")
    print(f"  Expiration: {credentials['expiration']}")
except Exception as e:
    print(f"❌ STS 凭证获取失败: {str(e)}")
```

---

## 🔐 安全最佳实践

### 1. 权限最小化原则

✅ **推荐**：
- 使用自定义策略，限制只能上传（`oss:PutObject` 等）
- 限制只能访问特定 Bucket
- 不授予删除、列表等权限

❌ **不推荐**：
- 使用 `AliyunOSSFullAccess`（除非必要）
- 授予 `oss:DeleteObject` 权限（除非业务需要）

### 2. STS Token 有效期

```python
# 推荐设置 1 小时
duration_seconds=3600  # 1 hour

# 不推荐设置过长
duration_seconds=43200  # 12 hours (过长)
```

**原因**：
- 1 小时足够完成大部分文件上传
- 即使 Token 泄露，影响时间窗口较小
- 断点续传支持，不怕 Token 过期

### 3. 条件限制（可选，高级）

在自定义策略中添加条件限制：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:PutObject"
      ],
      "Resource": [
        "acs:oss:*:*:yuntu-render/scenes/*"
      ],
      "Condition": {
        "IpAddress": {
          "acs:SourceIp": [
            "1.2.3.4/24"
          ]
        }
      }
    }
  ]
}
```

限制只能从特定 IP 段上传。

---

## 🌍 STS Endpoint 区域对照表

| 区域 | STS Endpoint | 说明 |
|------|-------------|------|
| 华北（北京） | `sts.cn-beijing.aliyuncs.com` | 推荐 |
| 华东（上海） | `sts.cn-shanghai.aliyuncs.com` | |
| 华南（深圳） | `sts.cn-shenzhen.aliyuncs.com` | |
| 中国（香港） | `sts.cn-hongkong.aliyuncs.com` | |
| 亚太（新加坡） | `sts.ap-southeast-1.aliyuncs.com` | |
| 美国（硅谷） | `sts.us-west-1.aliyuncs.com` | |

**选择建议**：选择与您的 OSS Bucket 同区域的 STS Endpoint。

---

## 🛠️ 故障排查

### 问题 1：NoSuchBucket

**错误信息**：
```
The specified bucket does not exist.
```

**解决方案**：
1. 检查 `OSS_BUCKET_NAME` 配置是否正确
2. 确认 Bucket 已创建
3. 检查 Bucket 区域与 Endpoint 是否匹配

### 问题 2：InvalidAccessKeyId.NotFound

**错误信息**：
```
The Access Key ID provided does not exist in our records.
```

**解决方案**：
1. 检查 `OSS_ACCESS_KEY_ID` 是否正确
2. 确认 AccessKey 未被禁用或删除
3. 检查是否使用了正确的阿里云账号

### 问题 3：NoPermission

**错误信息**：
```
You are not authorized to do this action.
```

**解决方案**：
1. 确认 RAM 角色已添加 `AliyunOSSFullAccess` 或自定义策略
2. 检查自定义策略中的 Action 是否包含所需权限
3. 检查 Resource 是否匹配目标 Bucket

### 问题 4：AssumeRole Failed

**错误信息**：
```
You are not authorized to assume this role.
```

**解决方案**：
1. 检查 RAM 用户是否有 `sts:AssumeRole` 权限
2. 确认角色的信任策略允许当前账号
3. 检查 `OSS_ROLE_ARN` 格式是否正确

---

## 📚 参考文档

- [阿里云 RAM 角色管理](https://help.aliyun.com/zh/ram/user-guide/create-a-ram-role-for-a-trusted-alibabacloud-account)
- [阿里云 STS 使用指南](https://help.aliyun.com/zh/ram/developer-reference/use-the-sts-openapi-example)
- [OSS 权限策略示例](https://help.aliyun.com/zh/oss/user-guide/common-examples-of-ram-policies)
