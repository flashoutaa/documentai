"""数据库引擎与会话（SQLAlchemy 2.0，兼容 SQLite / PostgreSQL）。"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # SQLite 下关闭连接池检查，避免多线程问题
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

# require.md 5.5 约束 5：开发期开启外键约束，提前暴露问题
if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
