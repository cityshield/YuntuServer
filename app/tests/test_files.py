"""
文件API测试
"""
import pytest
from httpx import AsyncClient
from io import BytesIO

from app.config import settings


@pytest.mark.file
@pytest.mark.api
class TestFileUpload:
    """文件上传测试"""

    async def test_upload_file_success(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试成功上传文件"""
        # 创建测试文件
        file_content = b"Test Maya Scene File Content"
        files = {
            "file": ("test_scene.ma", BytesIO(file_content), "application/octet-stream")
        }

        response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "file_path" in data["data"]
        assert "file_url" in data["data"]
        assert "file_size" in data["data"]

    async def test_upload_file_without_auth(self, client: AsyncClient):
        """测试未认证上传文件"""
        file_content = b"Test content"
        files = {
            "file": ("test.ma", BytesIO(file_content), "application/octet-stream")
        }

        response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            files=files
        )
        assert response.status_code == 401

    async def test_upload_large_file(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试上传大文件"""
        # 创建10MB的测试文件
        file_content = b"X" * (10 * 1024 * 1024)
        files = {
            "file": ("large_scene.ma", BytesIO(file_content), "application/octet-stream")
        }

        response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            headers=auth_headers,
            files=files
        )
        # 根据配置,可能成功或失败
        assert response.status_code in [200, 413]

    async def test_upload_invalid_file_type(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试上传无效文件类型"""
        file_content = b"Invalid content"
        files = {
            "file": ("test.exe", BytesIO(file_content), "application/x-msdownload")
        }

        response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 400
        data = response.json()
        assert "不支持的文件类型" in data["detail"]

    async def test_upload_empty_file(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试上传空文件"""
        files = {
            "file": ("empty.ma", BytesIO(b""), "application/octet-stream")
        }

        response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 400
        data = response.json()
        assert "文件不能为空" in data["detail"]

    async def test_upload_maya_scene_files(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试上传各种Maya场景文件格式"""
        extensions = [".ma", ".mb", ".zip", ".rar"]

        for ext in extensions:
            file_content = b"Test Maya Scene"
            files = {
                "file": (f"scene{ext}", BytesIO(file_content), "application/octet-stream")
            }

            response = await client.post(
                f"{settings.API_V1_PREFIX}/files/upload",
                headers=auth_headers,
                files=files
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200


@pytest.mark.file
@pytest.mark.api
class TestFileDownload:
    """文件下载测试"""

    async def test_get_download_url(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试获取下载URL"""
        # 先上传文件
        file_content = b"Test content for download"
        files = {
            "file": ("download_test.ma", BytesIO(file_content), "application/octet-stream")
        }

        upload_response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            headers=auth_headers,
            files=files
        )
        assert upload_response.status_code == 200

        # 获取下载URL
        file_path = upload_response.json()["data"]["file_path"]
        filename = file_path.split("/")[-1]

        # 模拟任务ID
        from uuid import uuid4
        task_id = uuid4()

        response = await client.get(
            f"{settings.API_V1_PREFIX}/files/download/{task_id}/{filename}",
            headers=auth_headers
        )
        # 可能返回重定向或下载URL
        assert response.status_code in [200, 302, 307]

    async def test_download_nonexistent_file(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试下载不存在的文件"""
        from uuid import uuid4
        task_id = uuid4()

        response = await client.get(
            f"{settings.API_V1_PREFIX}/files/download/{task_id}/nonexistent.ma",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_download_without_auth(self, client: AsyncClient):
        """测试未认证下载文件"""
        from uuid import uuid4
        task_id = uuid4()

        response = await client.get(
            f"{settings.API_V1_PREFIX}/files/download/{task_id}/test.ma"
        )
        assert response.status_code == 401


@pytest.mark.file
@pytest.mark.api
class TestFileList:
    """文件列表测试"""

    async def test_list_user_files(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试获取用户文件列表"""
        # 先上传几个文件
        for i in range(3):
            file_content = f"Test file {i}".encode()
            files = {
                "file": (f"test_{i}.ma", BytesIO(file_content), "application/octet-stream")
            }
            await client.post(
                f"{settings.API_V1_PREFIX}/files/upload",
                headers=auth_headers,
                files=files
            )

        # 获取文件列表
        response = await client.get(
            f"{settings.API_V1_PREFIX}/files/list",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert len(data["data"]["items"]) >= 3

    async def test_list_files_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试文件列表分页"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/files/list?page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10


@pytest.mark.file
@pytest.mark.api
class TestFileDelete:
    """文件删除测试"""

    async def test_delete_file_success(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试成功删除文件"""
        # 先上传文件
        file_content = b"File to delete"
        files = {
            "file": ("delete_test.ma", BytesIO(file_content), "application/octet-stream")
        }

        upload_response = await client.post(
            f"{settings.API_V1_PREFIX}/files/upload",
            headers=auth_headers,
            files=files
        )
        assert upload_response.status_code == 200
        file_path = upload_response.json()["data"]["file_path"]

        # 删除文件
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/files/delete",
            headers=auth_headers,
            json={"file_path": file_path}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_delete_nonexistent_file(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试删除不存在的文件"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/files/delete",
            headers=auth_headers,
            json={"file_path": "scenes/nonexistent/file.ma"}
        )
        assert response.status_code == 404

    async def test_delete_file_without_auth(self, client: AsyncClient):
        """测试未认证删除文件"""
        response = await client.delete(
            f"{settings.API_V1_PREFIX}/files/delete",
            json={"file_path": "scenes/test/file.ma"}
        )
        assert response.status_code == 401
