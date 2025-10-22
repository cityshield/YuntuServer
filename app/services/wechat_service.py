"""
微信登录服务
"""
import httpx
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User
from app.models.wechat_login_session import WechatLoginSession
from app.schemas.wechat import WechatUserInfo
from app.services.auth_service import auth_service
from app.services.sms_service import sms_service


class WechatService:
    """微信登录服务类"""

    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.redirect_uri = settings.WECHAT_REDIRECT_URI

        # 微信 API 端点
        self.auth_url = "https://open.weixin.qq.com/connect/qrconnect"
        self.access_token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        self.user_info_url = "https://api.weixin.qq.com/sns/userinfo"

    async def generate_qrcode(
        self,
        db: AsyncSession,
        device_type: str = "pc"
    ) -> Tuple[str, str, int]:
        """
        生成微信登录二维码

        Args:
            db: 数据库会话
            device_type: 设备类型 (pc/mobile)

        Returns:
            (scene_str, qr_code_url, expires_in)
        """
        # 生成唯一的场景值
        scene_str = str(uuid.uuid4())

        # 生成state参数（防CSRF）
        state = secrets.token_urlsafe(16)

        # 构建微信授权URL
        qr_code_url = (
            f"{self.auth_url}?"
            f"appid={self.app_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope=snsapi_login&"
            f"state={scene_str}#{state}"
        )

        # 创建登录会话记录
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        session = WechatLoginSession(
            scene_str=scene_str,
            qr_code_url=qr_code_url,
            state="pending",
            device_type=device_type,
            expires_at=expires_at
        )

        db.add(session)
        await db.commit()

        return scene_str, qr_code_url, 300  # 5分钟过期

    async def poll_session(
        self,
        db: AsyncSession,
        scene_str: str
    ) -> Dict:
        """
        轮询扫码登录状态

        Args:
            db: 数据库会话
            scene_str: 场景值

        Returns:
            状态信息字典
        """
        # 查询会话
        result = await db.execute(
            select(WechatLoginSession).where(
                WechatLoginSession.scene_str == scene_str
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        # 检查是否过期
        if datetime.utcnow() > session.expires_at:
            session.state = "expired"
            await db.commit()
            return {"status": "expired"}

        # 返回当前状态
        response = {"status": session.state}

        if session.state == "confirmed":
            # 已确认登录
            if session.user_id:
                # 已有账号，返回用户信息和token
                user = await db.get(User, session.user_id)
                access_token, refresh_token, expires_in = await auth_service.create_tokens(
                    db=db, user=user
                )

                response.update({
                    "user": {
                        "id": str(user.id),
                        "username": user.username,
                        "phone": user.phone,
                        "email": user.email,
                        "avatar": user.avatar or user.wechat_avatar
                    },
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_in": expires_in,
                    "need_bind_phone": False
                })
            else:
                # 需要绑定手机号
                response.update({
                    "need_bind_phone": True,
                    "session_token": session.session_token
                })

        return response

    async def get_access_token(self, code: str) -> Dict:
        """
        通过code获取微信access_token

        Args:
            code: 微信授权code

        Returns:
            包含access_token和openid的字典
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.access_token_url,
                params={
                    "appid": self.app_id,
                    "secret": self.app_secret,
                    "code": code,
                    "grant_type": "authorization_code"
                }
            )

            data = response.json()

            if "errcode" in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"获取微信access_token失败: {data.get('errmsg')}"
                )

            return data

    async def get_user_info(
        self,
        access_token: str,
        openid: str
    ) -> WechatUserInfo:
        """
        获取微信用户信息

        Args:
            access_token: 微信access_token
            openid: 微信openid

        Returns:
            微信用户信息
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_info_url,
                params={
                    "access_token": access_token,
                    "openid": openid
                }
            )

            data = response.json()

            if "errcode" in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"获取微信用户信息失败: {data.get('errmsg')}"
                )

            return WechatUserInfo(**data)

    async def handle_callback(
        self,
        db: AsyncSession,
        code: str,
        state: Optional[str] = None
    ) -> Dict:
        """
        处理微信授权回调

        Args:
            db: 数据库会话
            code: 微信授权code
            state: 状态参数（scene_str）

        Returns:
            处理结果
        """
        # 获取access_token和openid
        token_data = await self.get_access_token(code)
        access_token = token_data["access_token"]
        openid = token_data["openid"]

        # 获取用户信息
        wechat_user = await self.get_user_info(access_token, openid)

        # 检查该微信是否已绑定用户
        result = await db.execute(
            select(User).where(User.wechat_openid == openid)
        )
        user = result.scalar_one_or_none()

        if user:
            # 已绑定用户，直接登录
            access_token, refresh_token, expires_in = await auth_service.create_tokens(
                db=db, user=user
            )

            # 更新登录时间
            user.last_login_at = datetime.utcnow()
            await db.commit()

            # 如果有state（扫码登录），更新会话状态
            if state:
                await self._update_session_confirmed(db, state, user.id)

            return {
                "openid": openid,
                "user_exists": True,
                "need_bind_phone": False,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "phone": user.phone,
                    "email": user.email,
                    "avatar": user.avatar or user.wechat_avatar
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in
            }
        else:
            # 未绑定用户，需要绑定手机号
            session_token = secrets.token_urlsafe(32)

            # 如果有state（扫码登录），更新会话状态
            if state:
                result = await db.execute(
                    select(WechatLoginSession).where(
                        WechatLoginSession.scene_str == state
                    )
                )
                session = result.scalar_one_or_none()

                if session:
                    session.state = "scanned"
                    session.wechat_openid = openid
                    session.session_token = session_token
                    await db.commit()

            return {
                "openid": openid,
                "user_exists": False,
                "need_bind_phone": True,
                "session_token": session_token
            }

    async def bind_phone(
        self,
        db: AsyncSession,
        session_token: str,
        phone: str,
        verification_code: str
    ) -> Tuple[User, str, str, int]:
        """
        新用户绑定手机号完成注册

        Args:
            db: 数据库会话
            session_token: 临时会话token
            phone: 手机号
            verification_code: 验证码

        Returns:
            (user, access_token, refresh_token, expires_in)
        """
        # 验证短信验证码
        is_valid = await sms_service.verify_code(phone, verification_code)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码无效或已过期"
            )

        # 查找会话
        result = await db.execute(
            select(WechatLoginSession).where(
                WechatLoginSession.session_token == session_token
            )
        )
        session = result.scalar_one_or_none()

        if not session or not session.wechat_openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="会话无效"
            )

        # 检查手机号是否已被使用
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被注册"
            )

        # 获取微信用户信息
        token_data = await self.get_access_token(session.wechat_openid)  # 这里简化处理
        # 实际应该存储access_token，这里需要重新授权或使用refresh_token

        # 创建新用户
        password_hash = auth_service.hash_password(secrets.token_urlsafe(16))  # 随机密码
        user = User(
            username=phone,  # 使用手机号作为用户名
            phone=phone,
            password_hash=password_hash,
            wechat_openid=session.wechat_openid,
            wechat_bound_at=datetime.utcnow()
        )

        db.add(user)

        # 更新会话状态
        session.state = "confirmed"
        session.user_id = user.id
        session.confirmed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        # 生成token
        access_token, refresh_token, expires_in = await auth_service.create_tokens(
            db=db, user=user
        )

        return user, access_token, refresh_token, expires_in

    async def link_account(
        self,
        db: AsyncSession,
        session_token: str,
        phone: str,
        password: str
    ) -> Tuple[User, str, str, int]:
        """
        关联已有账号

        Args:
            db: 数据库会话
            session_token: 临时会话token
            phone: 手机号
            password: 密码

        Returns:
            (user, access_token, refresh_token, expires_in)
        """
        # 查找会话
        result = await db.execute(
            select(WechatLoginSession).where(
                WechatLoginSession.session_token == session_token
            )
        )
        session = result.scalar_one_or_none()

        if not session or not session.wechat_openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="会话无效"
            )

        # 验证用户账号密码
        result = await db.execute(
            select(User).where(User.phone == phone)
        )
        user = result.scalar_one_or_none()

        if not user or not auth_service.verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="手机号或密码错误"
            )

        # 检查该微信是否已被其他账号绑定
        if user.wechat_openid and user.wechat_openid != session.wechat_openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该账号已绑定其他微信"
            )

        # 绑定微信
        user.wechat_openid = session.wechat_openid
        user.wechat_bound_at = datetime.utcnow()
        user.last_login_at = datetime.utcnow()

        # 更新会话状态
        session.state = "confirmed"
        session.user_id = user.id
        session.confirmed_at = datetime.utcnow()

        await db.commit()

        # 生成token
        access_token, refresh_token, expires_in = await auth_service.create_tokens(
            db=db, user=user
        )

        return user, access_token, refresh_token, expires_in

    async def bind_wechat_to_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        code: str
    ) -> User:
        """
        已登录用户绑定微信

        Args:
            db: 数据库会话
            user_id: 用户ID
            code: 微信授权code

        Returns:
            更新后的用户对象
        """
        # 获取用户
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 获取微信信息
        token_data = await self.get_access_token(code)
        access_token = token_data["access_token"]
        openid = token_data["openid"]

        wechat_user = await self.get_user_info(access_token, openid)

        # 检查该微信是否已被其他账号绑定
        result = await db.execute(
            select(User).where(User.wechat_openid == openid)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该微信已被其他账号绑定"
            )

        # 绑定微信
        user.wechat_openid = openid
        user.wechat_unionid = wechat_user.unionid
        user.wechat_nickname = wechat_user.nickname
        user.wechat_avatar = wechat_user.headimgurl
        user.wechat_bound_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return user

    async def unbind_wechat(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> bool:
        """
        解绑微信

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            是否成功
        """
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        if not user.wechat_openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未绑定微信"
            )

        # 解绑
        user.wechat_openid = None
        user.wechat_unionid = None
        user.wechat_nickname = None
        user.wechat_avatar = None
        user.wechat_bound_at = None

        await db.commit()

        return True

    async def _update_session_confirmed(
        self,
        db: AsyncSession,
        scene_str: str,
        user_id: uuid.UUID
    ):
        """更新会话为已确认状态"""
        result = await db.execute(
            select(WechatLoginSession).where(
                WechatLoginSession.scene_str == scene_str
            )
        )
        session = result.scalar_one_or_none()

        if session:
            session.state = "confirmed"
            session.user_id = user_id
            session.confirmed_at = datetime.utcnow()
            await db.commit()


# 创建服务实例
wechat_service = WechatService()
