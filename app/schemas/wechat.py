"""
微信登录相关的 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ===== 请求 Schemas =====

class WechatQRCodeRequest(BaseModel):
    """生成微信登录二维码请求"""
    device_type: str = Field(..., description="设备类型：pc 或 mobile")


class WechatCallbackRequest(BaseModel):
    """微信授权回调请求"""
    code: str = Field(..., description="微信授权code")
    state: Optional[str] = Field(None, description="状态参数")


class WechatBindPhoneRequest(BaseModel):
    """绑定手机号请求（新用户注册）"""
    session_token: str = Field(..., description="临时会话token")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    verification_code: str = Field(..., min_length=6, max_length=6, description="短信验证码")


class WechatLinkAccountRequest(BaseModel):
    """关联已有账号请求"""
    session_token: str = Field(..., description="临时会话token")
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")
    password: str = Field(..., min_length=6, description="密码")


class WechatBindRequest(BaseModel):
    """绑定微信请求（已登录用户）"""
    code: str = Field(..., description="微信授权code")


# ===== 响应 Schemas =====

class WechatQRCodeResponse(BaseModel):
    """生成微信登录二维码响应"""
    scene_str: str = Field(..., description="场景值（用于轮询）")
    qr_code_url: str = Field(..., description="二维码URL")
    expires_in: int = Field(..., description="过期时间（秒）")


class WechatPollResponse(BaseModel):
    """轮询扫码状态响应"""
    status: str = Field(..., description="状态：pending/scanned/confirmed/expired")
    need_bind_phone: Optional[bool] = Field(None, description="是否需要绑定手机号")
    session_token: Optional[str] = Field(None, description="临时会话token（需要绑定时返回）")
    user: Optional[dict] = Field(None, description="用户信息（已绑定时返回）")
    access_token: Optional[str] = Field(None, description="访问令牌（confirmed时返回）")
    refresh_token: Optional[str] = Field(None, description="刷新令牌（confirmed时返回）")
    expires_in: Optional[int] = Field(None, description="令牌过期时间（confirmed时返回）")


class WechatCallbackResponse(BaseModel):
    """微信授权回调响应"""
    openid: str = Field(..., description="微信OpenID")
    user_exists: bool = Field(..., description="用户是否已存在")
    need_bind_phone: bool = Field(..., description="是否需要绑定手机号")
    session_token: Optional[str] = Field(None, description="临时会话token（需要绑定时返回）")
    user: Optional[dict] = Field(None, description="用户信息（已绑定时返回）")
    access_token: Optional[str] = Field(None, description="访问令牌（已绑定时返回）")
    refresh_token: Optional[str] = Field(None, description="刷新令牌（已绑定时返回）")
    expires_in: Optional[int] = Field(None, description="令牌过期时间（已绑定时返回）")


class WechatBindPhoneResponse(BaseModel):
    """绑定手机号响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    user: dict = Field(..., description="用户信息")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    expires_in: int = Field(..., description="令牌过期时间（秒）")


class WechatLinkAccountResponse(BaseModel):
    """关联已有账号响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    user: dict = Field(..., description="用户信息")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    expires_in: int = Field(..., description="令牌过期时间（秒）")


class WechatBindResponse(BaseModel):
    """绑定微信响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    wechat_nickname: Optional[str] = Field(None, description="微信昵称")
    wechat_avatar: Optional[str] = Field(None, description="微信头像")
    bound_at: datetime = Field(..., description="绑定时间")


class WechatUnbindResponse(BaseModel):
    """解绑微信响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")


# ===== 内部数据结构 =====

class WechatUserInfo(BaseModel):
    """微信用户信息"""
    openid: str
    unionid: Optional[str] = None
    nickname: Optional[str] = None
    headimgurl: Optional[str] = None
    sex: Optional[int] = None
    province: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
