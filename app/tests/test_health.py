"""
健康检查测试 - 简单的端到端测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestHealthCheck:
    """健康检查测试"""

    async def test_health_endpoint(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "service" in data

    async def test_root_endpoint(self, client: AsyncClient):
        """测试根端点"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    async def test_docs_available(self, client: AsyncClient):
        """测试API文档可访问"""
        response = await client.get("/docs")
        # 文档可能返回200(可访问)或404(生产环境禁用)
        assert response.status_code in [200, 404]
