"""
SQLAlchemy Base 模型
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
import uuid

Base = declarative_base()


# 自定义 UUID 类型，兼容 SQLite 和 PostgreSQL
class UUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as string.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


# 导入所有模型，确保 Alembic 可以检测到
def import_models():
    """导入所有模型以供 Alembic 使用"""
    from app.models import user  # noqa
    from app.models import task  # noqa
    from app.models import transaction  # noqa
    from app.models import refresh_token  # noqa
