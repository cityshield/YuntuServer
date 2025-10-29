"""
批量创建测试用户脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.drive import Drive
from app.core.security import get_password_hash
from app.config import settings
from datetime import datetime


async def create_test_users():
    """批量创建测试用户"""
    # 创建数据库引擎
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)

    # 创建会话工厂
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # 统一密码
    password = "yuntu123"
    password_hash = get_password_hash(password)

    # 起始手机号
    base_phone = 13000000000

    async with async_session() as session:
        created_count = 0
        skipped_count = 0

        print("开始创建测试用户...")
        print(f"总数: 150 个用户")
        print(f"起始手机号: {base_phone}")
        print(f"统一密码: {password}")
        print("-" * 50)

        for i in range(150):
            # 生成用户名和手机号
            username = f"testuser{i+1:03d}"  # testuser001, testuser002, ...
            phone = str(base_phone + i)  # 13000000000, 13000000001, ...

            try:
                # 检查用户是否已存在
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(
                        (User.username == username) | (User.phone == phone)
                    )
                )
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    print(f"跳过 {username} ({phone}) - 已存在")
                    skipped_count += 1
                    continue

                # 创建新用户
                new_user = User(
                    username=username,
                    password_hash=password_hash,
                    phone=phone,
                    balance=0.00,
                    member_level=0,  # 普通用户
                    is_active=True,
                    last_login_at=datetime.utcnow(),
                )

                session.add(new_user)
                await session.flush()
                await session.refresh(new_user)

                # 为新用户创建默认盘符
                default_drive = Drive(
                    name="默认盘",
                    icon="📁",
                    description="系统自动创建的默认盘符",
                    total_size=None,  # 无限制
                    is_team_drive=False,
                    user_id=new_user.id,
                    team_id=None,
                )
                session.add(default_drive)
                await session.flush()

                created_count += 1

                # 每 10 个用户提交一次
                if (i + 1) % 10 == 0:
                    await session.commit()
                    print(f"已创建 {created_count} 个用户...")

            except Exception as e:
                print(f"创建用户 {username} 失败: {e}")
                await session.rollback()
                continue

        # 最后提交一次
        await session.commit()

        print("-" * 50)
        print(f"✅ 创建完成!")
        print(f"成功创建: {created_count} 个用户")
        print(f"跳过已存在: {skipped_count} 个用户")
        print(f"总计: {created_count + skipped_count}")
        print()
        print("用户信息:")
        print(f"  用户名: testuser001 ~ testuser150")
        print(f"  手机号: {base_phone} ~ {base_phone + 149}")
        print(f"  密码: {password}")
        print(f"  会员等级: 0 (普通用户)")
        print(f"  余额: 0.00")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_users())
