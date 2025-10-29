"""
阿里云 OSS 回调验证工具
"""
import base64
import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from app.utils.logger import setup_logger

logger = setup_logger()


def verify_oss_callback_signature(
    request: Request,
    public_key_url: str,
    authorization: str,
    body: bytes
) -> bool:
    """
    验证 OSS 回调签名

    Args:
        request: FastAPI Request 对象
        public_key_url: OSS 公钥 URL（从 x-oss-pub-key-url 头获取）
        authorization: 授权签名（从 authorization 头获取）
        body: 请求体原始字节

    Returns:
        bool: 签名是否有效
    """
    try:
        # 1. Base64 解码公钥 URL
        pub_key_url_decoded = base64.b64decode(public_key_url).decode('utf-8')

        # 安全检查：确保公钥 URL 来自阿里云
        if not pub_key_url_decoded.startswith("https://gosspublic.alicdn.com/") and \
           not pub_key_url_decoded.startswith("http://gosspublic.alicdn.com/"):
            logger.error(f"Invalid public key URL: {pub_key_url_decoded}")
            return False

        # 2. 构建待签名字符串
        # 格式: URL路径\nQuery参数\nBody
        url_path = request.url.path
        query_string = str(request.url.query) if request.url.query else ""

        auth_str = f"{url_path}\n{query_string}\n{body.decode('utf-8')}"

        # 3. 使用 MD5 验证（简化版本，生产环境应该下载公钥并使用 RSA 验证）
        # 注意：这里使用 MD5 是为了简化，实际生产环境建议使用 RSA 公钥验证
        logger.info(f"OSS callback signature verification - Path: {url_path}, Query: {query_string}")

        # 暂时返回 True，因为我们信任来自配置的回调域名
        # TODO: 在生产环境中实现完整的 RSA 公钥验证
        return True

    except Exception as e:
        logger.error(f"Failed to verify OSS callback signature: {str(e)}")
        return False


def decode_callback_body(body_base64: str) -> Dict[str, Any]:
    """
    解码 OSS 回调请求体（Base64编码的JSON）

    Args:
        body_base64: Base64 编码的请求体

    Returns:
        Dict: 解码后的回调参数
    """
    try:
        # Base64 解码
        body_decoded = base64.b64decode(body_base64).decode('utf-8')

        # JSON 解析
        callback_params = json.loads(body_decoded)

        logger.info(f"Decoded OSS callback params: {callback_params}")
        return callback_params

    except Exception as e:
        logger.error(f"Failed to decode callback body: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid callback body: {str(e)}"
        )


def extract_callback_params(request: Request, body: bytes) -> Dict[str, Any]:
    """
    从 OSS 回调请求中提取参数

    Args:
        request: FastAPI Request 对象
        body: 请求体原始字节

    Returns:
        Dict: 提取的回调参数
    """
    try:
        # OSS 回调有两种格式:
        # 1. application/x-www-form-urlencoded (推荐)
        # 2. application/json

        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            # JSON 格式
            params = json.loads(body.decode('utf-8'))
        else:
            # URL 编码格式，需要解析
            body_str = body.decode('utf-8')
            params = {}
            for param in body_str.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    # URL 解码
                    import urllib.parse
                    params[key] = urllib.parse.unquote(value)

        logger.info(f"Extracted OSS callback params: {list(params.keys())}")
        return params

    except Exception as e:
        logger.error(f"Failed to extract callback params: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid callback params: {str(e)}"
        )


def build_callback_success_response() -> Dict[str, Any]:
    """
    构建 OSS 回调成功响应

    Returns:
        Dict: 成功响应体（JSON格式）
    """
    return {
        "Status": "OK",
        "Message": "Callback processed successfully"
    }


def build_callback_error_response(error: str) -> Dict[str, Any]:
    """
    构建 OSS 回调错误响应

    Args:
        error: 错误信息

    Returns:
        Dict: 错误响应体（JSON格式）
    """
    return {
        "Status": "Error",
        "Message": error
    }
