"""
任务API测试
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.config import settings
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskStatus


@pytest.mark.task
@pytest.mark.api
class TestTaskCreate:
    """任务创建测试"""

    async def test_create_task_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        fake_task_data: dict
    ):
        """测试成功创建任务"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/tasks/",
            headers=auth_headers,
            json=fake_task_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == fake_task_data["name"]
        assert data["data"]["status"] == TaskStatus.PENDING
        assert "id" in data["data"]

    async def test_create_task_without_auth(
        self,
        client: AsyncClient,
        fake_task_data: dict
    ):
        """测试未认证创建任务"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/tasks/",
            json=fake_task_data
        )
        assert response.status_code == 401

    async def test_create_task_insufficient_balance(
        self,
        client: AsyncClient,
        auth_headers: dict,
        fake_task_data: dict
    ):
        """测试余额不足创建任务"""
        # 创建一个大任务,消耗所有余额
        large_task_data = fake_task_data.copy()
        large_task_data["start_frame"] = 1
        large_task_data["end_frame"] = 1000  # 1000帧,消耗500元

        response = await client.post(
            f"{settings.API_V1_PREFIX}/tasks/",
            headers=auth_headers,
            json=large_task_data
        )
        assert response.status_code == 400
        data = response.json()
        assert "余额不足" in data["detail"]

    async def test_create_task_invalid_frame_range(
        self,
        client: AsyncClient,
        auth_headers: dict,
        fake_task_data: dict
    ):
        """测试无效帧范围"""
        invalid_data = fake_task_data.copy()
        invalid_data["start_frame"] = 100
        invalid_data["end_frame"] = 50  # 结束帧小于开始帧

        response = await client.post(
            f"{settings.API_V1_PREFIX}/tasks/",
            headers=auth_headers,
            json=invalid_data
        )
        assert response.status_code == 422

    async def test_create_task_missing_required_fields(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试缺少必填字段"""
        response = await client.post(
            f"{settings.API_V1_PREFIX}/tasks/",
            headers=auth_headers,
            json={
                "name": "Test Task"
                # 缺少其他必填字段
            }
        )
        assert response.status_code == 422


@pytest.mark.task
@pytest.mark.api
class TestTaskList:
    """任务列表测试"""

    @pytest.fixture
    async def test_task(
        self,
        db_session: AsyncSession,
        test_user: User
    ) -> Task:
        """创建测试任务"""
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            name="测试任务",
            scene_file="scenes/test/test.ma",
            maya_version="2024",
            renderer="arnold",
            start_frame=1,
            end_frame=10,
            status=TaskStatus.PENDING,
            priority=1,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        return task

    async def test_get_tasks_list(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_task: Task
    ):
        """测试获取任务列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert len(data["data"]["items"]) > 0

    async def test_get_tasks_empty(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试获取空任务列表"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 0

    async def test_get_tasks_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_task: Task
    ):
        """测试任务列表分页"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/?page=1&page_size=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 5

    async def test_get_tasks_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_task: Task
    ):
        """测试按状态筛选任务"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/?status={TaskStatus.PENDING}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        # 验证所有任务都是pending状态
        for task in data["data"]["items"]:
            assert task["status"] == TaskStatus.PENDING


@pytest.mark.task
@pytest.mark.api
class TestTaskDetail:
    """任务详情测试"""

    @pytest.fixture
    async def test_task(
        self,
        db_session: AsyncSession,
        test_user: User
    ) -> Task:
        """创建测试任务"""
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            name="详情测试任务",
            scene_file="scenes/test/detail.ma",
            maya_version="2024",
            renderer="arnold",
            start_frame=1,
            end_frame=50,
            status=TaskStatus.PENDING,
            priority=2,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        return task

    async def test_get_task_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_task: Task
    ):
        """测试获取任务详情"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/{test_task.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["id"] == str(test_task.id)
        assert data["data"]["name"] == test_task.name

    async def test_get_task_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试获取不存在的任务"""
        fake_id = uuid4()
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_get_other_user_task(
        self,
        client: AsyncClient,
        auth_headers2: dict,
        test_task: Task
    ):
        """测试获取其他用户的任务"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/{test_task.id}",
            headers=auth_headers2
        )
        assert response.status_code == 403


@pytest.mark.task
@pytest.mark.api
class TestTaskControl:
    """任务控制测试"""

    @pytest.fixture
    async def running_task(
        self,
        db_session: AsyncSession,
        test_user: User
    ) -> Task:
        """创建运行中的任务"""
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            name="运行中任务",
            scene_file="scenes/test/running.ma",
            maya_version="2024",
            renderer="arnold",
            start_frame=1,
            end_frame=100,
            status=TaskStatus.RUNNING,
            priority=1,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        return task

    async def test_pause_task(
        self,
        client: AsyncClient,
        auth_headers: dict,
        running_task: Task
    ):
        """测试暂停任务"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/tasks/{running_task.id}/pause",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_resume_task(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User
    ):
        """测试恢复任务"""
        # 创建暂停的任务
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            name="暂停任务",
            scene_file="scenes/test/paused.ma",
            maya_version="2024",
            renderer="arnold",
            start_frame=1,
            end_frame=100,
            status=TaskStatus.PAUSED,
            priority=1,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.put(
            f"{settings.API_V1_PREFIX}/tasks/{task.id}/resume",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_cancel_task(
        self,
        client: AsyncClient,
        auth_headers: dict,
        running_task: Task
    ):
        """测试取消任务"""
        response = await client.put(
            f"{settings.API_V1_PREFIX}/tasks/{running_task.id}/cancel",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_delete_task(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User
    ):
        """测试删除任务"""
        # 创建完成的任务
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            name="待删除任务",
            scene_file="scenes/test/delete.ma",
            maya_version="2024",
            renderer="arnold",
            start_frame=1,
            end_frame=10,
            status=TaskStatus.COMPLETED,
            priority=1,
        )
        db_session.add(task)
        await db_session.commit()

        response = await client.delete(
            f"{settings.API_V1_PREFIX}/tasks/{task.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


@pytest.mark.task
@pytest.mark.api
class TestTaskLogs:
    """任务日志测试"""

    @pytest.fixture
    async def task_with_logs(
        self,
        db_session: AsyncSession,
        test_user: User
    ) -> Task:
        """创建带日志的任务"""
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            name="日志测试任务",
            scene_file="scenes/test/logs.ma",
            maya_version="2024",
            renderer="arnold",
            start_frame=1,
            end_frame=10,
            status=TaskStatus.RUNNING,
            priority=1,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        return task

    async def test_get_task_logs(
        self,
        client: AsyncClient,
        auth_headers: dict,
        task_with_logs: Task
    ):
        """测试获取任务日志"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/{task_with_logs.id}/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert isinstance(data["data"]["items"], list)

    async def test_get_task_logs_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict,
        task_with_logs: Task
    ):
        """测试任务日志分页"""
        response = await client.get(
            f"{settings.API_V1_PREFIX}/tasks/{task_with_logs.id}/logs?page=1&page_size=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10
