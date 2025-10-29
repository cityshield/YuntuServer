"""
用户API测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.config import settings
from app.models.user import User


@pytest.mark.user
@pytest.mark.api
class TestUserInfo:
    """用户信息测试"""

    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """测试获取当前用户信息"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["username"] == "testuser"
        assert data["data"]["email"] == "test@example.com"
        assert "hashed_password" not in data["data"]

    async def test_get_current_user_without_auth(self, client: AsyncClient):
        """测试未认证获取用户信息"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/me"
        )
        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """测试无效Token获取用户信息"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    async def test_update_user_profile(self, client: AsyncClient, auth_headers: dict):
        """测试更新用户资料"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/users/me",
            headers=auth_headers,
            json={
                "nickname": "新昵称",
                "avatar": "https://example.com/avatar.jpg"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["nickname"] == "新昵称"
        assert data["data"]["avatar"] == "https://example.com/avatar.jpg"

    async def test_update_user_email(self, client: AsyncClient, auth_headers: dict):
        """测试更新邮箱"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/users/me",
            headers=auth_headers,
            json={
                "email": "newemail@example.com"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["email"] == "newemail@example.com"

    async def test_update_user_duplicate_email(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user2: User
    ):
        """测试更新为已存在的邮箱"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/users/me",
            headers=auth_headers,
            json={
                "email": "test2@example.com"  # test_user2的邮箱
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "邮箱已被使用" in data["detail"]


@pytest.mark.user
@pytest.mark.api
class TestUserBalance:
    """用户余额测试"""

    async def test_get_balance(self, client: AsyncClient, auth_headers: dict):
        """测试获取余额"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/balance",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "balance" in data["data"]
        assert isinstance(data["data"]["balance"], (int, float))

    async def test_recharge(self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        """测试充值"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/users/recharge",
            headers=auth_headers,
            json={
                "amount": 50.0,
                "payment_method": "alipay"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "balance" in data["data"]
        # 验证余额增加了50
        assert data["data"]["balance"] == 150.0  # 初始100 + 50

    async def test_recharge_invalid_amount(self, client: AsyncClient, auth_headers: dict):
        """测试无效充值金额"""
        # 负数
        response = await client.post(
            f"{settings.API_V1_PREFIX}/users/recharge",
            headers=auth_headers,
            json={
                "amount": -10.0,
                "payment_method": "alipay"
            }
        )
        assert response.status_code == 422

        # 零
        response = await client.post(
            f"{settings.API_V1_PREFIX}/users/recharge",
            headers=auth_headers,
            json={
                "amount": 0,
                "payment_method": "alipay"
            }
        )
        assert response.status_code == 422

    async def test_recharge_too_large(self, client: AsyncClient, auth_headers: dict):
        """测试充值金额过大"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/users/recharge",
            headers=auth_headers,
            json={
                "amount": 1000000.0,
                "payment_method": "alipay"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "单次充值金额不能超过" in data["detail"]


@pytest.mark.user
@pytest.mark.api
class TestUserTransactions:
    """用户交易记录测试"""

    async def test_get_transactions_empty(self, client: AsyncClient, auth_headers: dict):
        """测试获取空交易记录"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/transactions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert isinstance(data["data"]["items"], list)
        assert data["data"]["total"] == 0

    async def test_get_transactions_after_recharge(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试充值后的交易记录"""
        # 先充值
        await client.post(
            f"{settings.API_V1_PREFIX}/users/recharge",
            headers=auth_headers,
            json={
                "amount": 100.0,
                "payment_method": "wechat"
            }
        )

        # 获取交易记录
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/transactions",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) > 0

        # 验证第一条记录
        transaction = data["data"]["items"][0]
        assert transaction["type"] == "recharge"
        assert transaction["amount"] == 100.0

    async def test_get_transactions_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试交易记录分页"""
        # 创建多条交易记录
        for _ in range(5):
            await client.post(
                f"{settings.API_V1_PREFIX}/users/recharge",
                headers=auth_headers,
                json={
                    "amount": 10.0,
                    "payment_method": "alipay"
                }
            )

        # 测试分页
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/transactions?page=1&page_size=3",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 3
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 3
        assert data["data"]["total"] >= 5

    async def test_get_transactions_filter_by_type(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试按类型筛选交易记录"""
        # 充值
        await client.post(
            f"{settings.API_V1_PREFIX}/users/recharge",
            headers=auth_headers,
            json={
                "amount": 50.0,
                "payment_method": "alipay"
            }
        )

        # 获取充值类型的交易记录
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/transactions?type=recharge",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        # 验证所有记录都是充值类型
        for transaction in data["data"]["items"]:
            assert transaction["type"] == "recharge"


@pytest.mark.user
@pytest.mark.api
class TestUserBills:
    """用户账单测试"""

    async def test_get_bills_empty(self, client: AsyncClient, auth_headers: dict):
        """测试获取空账单"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/bills",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert isinstance(data["data"]["items"], list)

    async def test_get_bills_pagination(self, client: AsyncClient, auth_headers: dict):
        """测试账单分页"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/users/bills?page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10
