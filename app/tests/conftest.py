"""
测试配置和Fixtures
"""
import os
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from faker import Faker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.core.security import get_password_hash
from app.config import settings

# 创建Faker实例
fake = Faker('zh_CN')

# 测试数据库URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

# 创建测试会话工厂
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # 创建会话
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # 清理
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        phone="13800138000",
        hashed_password=get_password_hash("password123"),
        balance=100.0,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user2(db_session: AsyncSession) -> User:
    """创建第二个测试用户"""
    user = User(
        id=uuid4(),
        username="testuser2",
        email="test2@example.com",
        phone="13800138001",
        hashed_password=get_password_hash("password123"),
        balance=200.0,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: User) -> dict:
    """获取认证头"""
    # 登录获取token
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "username": "testuser",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    access_token = data["data"]["access_token"]

    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def auth_headers2(client: AsyncClient, test_user2: User) -> dict:
    """获取第二个用户的认证头"""
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        json={
            "username": "testuser2",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    access_token = data["data"]["access_token"]

    return {"Authorization": f"Bearer {access_token}"}


# 测试数据生成器
@pytest.fixture
def fake_user_data() -> dict:
    """生成假用户数据"""
    return {
        "username": fake.user_name(),
        "email": fake.email(),
        "phone": fake.phone_number()[:11],
        "password": "Test@123456"
    }


@pytest.fixture
def fake_task_data() -> dict:
    """生成假任务数据"""
    return {
        "name": fake.sentence(nb_words=3),
        "scene_file": f"scenes/{uuid4()}/test.ma",
        "maya_version": "2024",
        "renderer": "arnold",
        "start_frame": 1,
        "end_frame": 100,
        "priority": 1,
        "resolution_x": 1920,
        "resolution_y": 1080,
    }


# 环境变量配置
@pytest.fixture(scope="session", autouse=True)
def set_test_settings():
    """设置测试环境变量"""
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["TESTING"] = "1"
    os.environ["DEBUG"] = "True"
    os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # 使用测试Redis数据库
