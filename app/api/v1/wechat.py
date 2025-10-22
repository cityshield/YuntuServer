"""
微信登录相关的 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.wechat import (
    WechatQRCodeRequest,
    WechatQRCodeResponse,
    WechatPollResponse,
    WechatCallbackRequest,
    WechatCallbackResponse,
    WechatBindPhoneRequest,
    WechatBindPhoneResponse,
    WechatLinkAccountRequest,
    WechatLinkAccountResponse,
    WechatBindRequest,
    WechatBindResponse,
    WechatUnbindResponse,
)
from app.services.wechat_service import wechat_service
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/wechat", tags=["微信登录"])


@router.post(
    "/qrcode",
    response_model=WechatQRCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="生成微信登录二维码",
    description="生成微信扫码登录的二维码URL，返回场景值用于轮询状态"
)
async def generate_qrcode(
    request: WechatQRCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    生成微信登录二维码（PC端）

    - **device_type**: 设备类型（pc/mobile）

    返回二维码URL和场景值
    """
    scene_str, qr_code_url, expires_in = await wechat_service.generate_qrcode(
        db=db,
        device_type=request.device_type
    )

    return WechatQRCodeResponse(
        scene_str=scene_str,
        qr_code_url=qr_code_url,
        expires_in=expires_in
    )


@router.get(
    "/poll/{scene_str}",
    response_model=WechatPollResponse,
    status_code=status.HTTP_200_OK,
    summary="轮询扫码状态",
    description="前端轮询此接口获取扫码登录状态"
)
async def poll_scan_status(
    scene_str: str,
    db: AsyncSession = Depends(get_db)
):
    """
    轮询扫码登录状态

    - **scene_str**: 场景值（从生成二维码接口返回）

    返回当前状态：
    - pending: 等待扫码
    - scanned: 已扫码，等待确认
    - confirmed: 已确认登录
    - expired: 已过期
    """
    result = await wechat_service.poll_session(db=db, scene_str=scene_str)

    return WechatPollResponse(**result)


@router.post(
    "/callback",
    response_model=WechatCallbackResponse,
    status_code=status.HTTP_200_OK,
    summary="微信授权回调",
    description="处理微信授权后的回调，获取用户信息并判断是否需要绑定手机号"
)
async def wechat_callback(
    request: WechatCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    微信授权回调处理

    - **code**: 微信授权code
    - **state**: 状态参数（可选，扫码登录时使用）

    返回用户信息或提示需要绑定手机号
    """
    result = await wechat_service.handle_callback(
        db=db,
        code=request.code,
        state=request.state
    )

    return WechatCallbackResponse(**result)


@router.post(
    "/bind-phone",
    response_model=WechatBindPhoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="绑定手机号",
    description="新用户首次微信登录后绑定手机号完成注册"
)
async def bind_phone(
    request: WechatBindPhoneRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    新用户绑定手机号完成注册

    - **session_token**: 临时会话token
    - **phone**: 手机号
    - **verification_code**: 短信验证码

    返回用户信息和访问令牌
    """
    user, access_token, refresh_token, expires_in = await wechat_service.bind_phone(
        db=db,
        session_token=request.session_token,
        phone=request.phone,
        verification_code=request.verification_code
    )

    return WechatBindPhoneResponse(
        success=True,
        message="注册成功",
        user={
            "id": str(user.id),
            "username": user.username,
            "phone": user.phone,
            "email": user.email,
            "avatar": user.avatar or user.wechat_avatar
        },
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post(
    "/link-account",
    response_model=WechatLinkAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="关联已有账号",
    description="首次微信登录时关联已有账号"
)
async def link_account(
    request: WechatLinkAccountRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    关联已有账号

    - **session_token**: 临时会话token
    - **phone**: 手机号
    - **password**: 密码

    返回用户信息和访问令牌
    """
    user, access_token, refresh_token, expires_in = await wechat_service.link_account(
        db=db,
        session_token=request.session_token,
        phone=request.phone,
        password=request.password
    )

    return WechatLinkAccountResponse(
        success=True,
        message="关联成功",
        user={
            "id": str(user.id),
            "username": user.username,
            "phone": user.phone,
            "email": user.email,
            "avatar": user.avatar or user.wechat_avatar
        },
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in
    )


@router.post(
    "/bind",
    response_model=WechatBindResponse,
    status_code=status.HTTP_200_OK,
    summary="绑定微信",
    description="已登录用户在个人中心绑定微信"
)
async def bind_wechat(
    request: WechatBindRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    已登录用户绑定微信

    - **code**: 微信授权code

    返回绑定结果
    """
    user = await wechat_service.bind_wechat_to_user(
        db=db,
        user_id=current_user.id,
        code=request.code
    )

    return WechatBindResponse(
        success=True,
        message="绑定成功",
        wechat_nickname=user.wechat_nickname,
        wechat_avatar=user.wechat_avatar,
        bound_at=user.wechat_bound_at
    )


@router.delete(
    "/unbind",
    response_model=WechatUnbindResponse,
    status_code=status.HTTP_200_OK,
    summary="解绑微信",
    description="已登录用户解绑微信"
)
async def unbind_wechat(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    解绑微信

    需要登录状态

    返回解绑结果
    """
    await wechat_service.unbind_wechat(
        db=db,
        user_id=current_user.id
    )

    return WechatUnbindResponse(
        success=True,
        message="解绑成功"
    )
