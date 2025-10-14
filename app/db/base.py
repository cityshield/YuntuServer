"""
SQLAlchemy Base 模型
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# 导入所有模型，确保 Alembic 可以检测到
def import_models():
    """导入所有模型以供 Alembic 使用"""
    from app.models import user  # noqa
    from app.models import task  # noqa
    from app.models import transaction  # noqa
    from app.models import refresh_token  # noqa
