"""
批量更新用户头像脚本
使用 DiceBear Avatars API 生成头像
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.user import User
from app.config import settings


# DiceBear Avatars API
# 可用的风格: adventurer, avataaars, big-ears, bottts, croodles, fun-emoji, identicon, lorelei, micah, miniavs, personas, pixel-art, thumbs
AVATAR_STYLES = [
    "adventurer",
    "avataaars",
    "bottts",
    "pixel-art",
    "personas",
    "lorelei",
    "micah",
    "miniavs"
]


def get_avatar_url(username: str, style: str = "avataaars") -> str:
    """
    生成 DiceBear 头像 URL

    Args:
        username: 用户名（用作种子）
        style: 头像风格

    Returns:
        头像 URL
    """
    # DiceBear API v7
    return f"https://api.dicebear.com/7.x/{style}/svg?seed={username}"


async def update_user_avatars():
    """批量更新用户头像"""
    # 创建数据库引擎
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url, echo=False)

    # 创建会话工厂
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        print("开始更新用户头像...")
        print(f"使用 DiceBear Avatars API")
        print(f"可用风格数: {len(AVATAR_STYLES)}")
        print("-" * 50)

        # 查询所有用户
        result = await session.execute(
            select(User).order_by(User.created_at)
        )
        users = result.scalars().all()

        total_users = len(users)
        updated_count = 0
        skipped_count = 0

        print(f"找到 {total_users} 个用户")
        print("-" * 50)

        for i, user in enumerate(users):
            try:
                # 为每个用户循环使用不同的头像风格
                style = AVATAR_STYLES[i % len(AVATAR_STYLES)]

                # 生成头像 URL
                avatar_url = get_avatar_url(user.username, style)

                # 如果用户已有头像且不想覆盖，可以跳过
                # if user.avatar:
                #     print(f"跳过 {user.username} - 已有头像")
                #     skipped_count += 1
                #     continue

                # 更新头像
                user.avatar = avatar_url
                updated_count += 1

                # 每处理 20 个用户提交一次
                if (i + 1) % 20 == 0:
                    await session.commit()
                    print(f"已更新 {updated_count} 个用户头像... ({style})")

            except Exception as e:
                print(f"更新用户 {user.username} 头像失败: {e}")
                await session.rollback()
                continue

        # 最后提交一次
        await session.commit()

        print("-" * 50)
        print(f"✅ 更新完成!")
        print(f"成功更新: {updated_count} 个用户")
        print(f"跳过: {skipped_count} 个用户")
        print(f"总计: {total_users}")
        print()
        print("头像 API 示例:")
        print(f"  {get_avatar_url('testuser001', 'avataaars')}")
        print()
        print("提示: 头像会实时从 DiceBear API 生成，无需下载存储")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_user_avatars())
