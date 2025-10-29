"""
认证API测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User


@pytest.mark.auth
@pytest.mark.api
class TestAuthRegister:
    """注册测试"""

    async def test_register_success(self, client: AsyncClient):
        """测试成功注册"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "phone": "13900139000",
                "verification_code": "123456",
                "password": "Password@123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "注册成功"
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    async def test_register_duplicate_username(self, client: AsyncClient, test_user: User):
        """测试重复用户名"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "username": "testuser",  # 已存在
                "email": "another@example.com",
                "phone": "13900139001",
                "verification_code": "123456",
                "password": "Password@123"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "用户名已存在" in data["detail"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """测试重复邮箱"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "username": "newuser2",
                "email": "test@example.com",  # 已存在
                "phone": "13900139002",
                "verification_code": "123456",
                "password": "Password@123"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "邮箱已被注册" in data["detail"]

    async def test_register_duplicate_phone(self, client: AsyncClient, test_user: User):
        """测试重复手机号"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "username": "newuser3",
                "email": "another2@example.com",
                "phone": "13800138000",  # 已存在
                "verification_code": "123456",
                "password": "Password@123"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "手机号已被注册" in data["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        """测试无效邮箱"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "username": "newuser4",
                "email": "invalid-email",
                "phone": "13900139003",
                "verification_code": "123456",
                "password": "Password@123"
            }
        )
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        """测试密码太短"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/register",
            json={
                "username": "newuser5",
                "email": "test5@example.com",
                "phone": "13900139004",
                "verification_code": "123456",
                "password": "123"
            }
        )
        assert response.status_code == 422


@pytest.mark.auth
@pytest.mark.api
class TestAuthLogin:
    """登录测试"""

    async def test_login_with_username_success(self, client: AsyncClient, test_user: User):
        """测试使用用户名登录成功"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    async def test_login_with_email_success(self, client: AsyncClient, test_user: User):
        """测试使用邮箱登录成功"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "test@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """测试密码错误"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        data = response.json()
        assert "用户名或密码错误" in data["detail"]

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == 401
        data = response.json()
        assert "用户名或密码错误" in data["detail"]

    async def test_login_missing_fields(self, client: AsyncClient):
        """测试缺少字段"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "testuser"
            }
        )
        assert response.status_code == 422


@pytest.mark.auth
@pytest.mark.api
class TestAuthRefresh:
    """Token刷新测试"""

    async def test_refresh_token_success(self, client: AsyncClient, test_user: User):
        """测试成功刷新Token"""
        # 先登录获取refresh_token
        login_response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data["data"]["refresh_token"]

        # 使用refresh_token获取新的access_token
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={
                "refresh_token": refresh_token
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """测试无效的refresh_token"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/refresh",
            json={
                "refresh_token": "invalid_token"
            }
        )
        assert response.status_code == 401


@pytest.mark.auth
@pytest.mark.api
class TestAuthLogout:
    """登出测试"""

    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功登出"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/logout",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "登出成功"

    async def test_logout_without_auth(self, client: AsyncClient):
        """测试未认证登出"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/logout"
        )
        assert response.status_code == 401

    async def test_logout_invalid_token(self, client: AsyncClient):
        """测试无效Token登出"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/logout",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


@pytest.mark.auth
@pytest.mark.api
class TestAuthSendCode:
    """发送验证码测试"""

    async def test_send_code_success(self, client: AsyncClient):
        """测试成功发送验证码"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/send-code",
            json={
                "phone": "13900139999"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "验证码已发送" in data["message"] or "模拟模式" in data["message"]

    async def test_send_code_invalid_phone(self, client: AsyncClient):
        """测试无效手机号"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/auth/send-code",
            json={
                "phone": "123"
            }
        )
        assert response.status_code == 422
