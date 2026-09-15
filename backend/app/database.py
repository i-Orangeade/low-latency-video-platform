# 数据库基础设施模块。
# 负责三件事：创建 SQLAlchemy 引擎、为每个请求提供独立 Session、初始化数据表。
# engine 和 SessionLocal 使用全局变量，是为了让测试可以先切换到临时 SQLite 数据库。
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = None
SessionLocal = None
is_sqlite = True


class Base(DeclarativeBase):
    # SQLAlchemy 2.x 声明式基类。
    # 所有模型都继承 Base，表结构会被统一注册到 Base.metadata。
    pass


def configure_engine(database_url: str | None = None) -> None:
    # 允许传入 database_url 主要用于测试；正常启动时读取 settings.database_url。
    global engine, SessionLocal, is_sqlite
    url = database_url or settings.database_url
    is_sqlite = url.startswith("sqlite")
    # FastAPI 可能在线程池中执行同步路由，因此 SQLite 连接不能限制为创建它的线程。
    # timeout 表示遇到锁时等待 30 秒，而不是立刻抛出 database is locked。
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(url, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    # FastAPI 的依赖注入会为每个请求调用该函数。
    # yield 之前创建 Session，请求处理结束后在 finally 中关闭，避免连接泄漏。
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # 导入模型后，Base.metadata 才知道项目中存在哪些表。
    from app.models import device  # noqa: F401

    if engine is None:
        configure_engine()
    if is_sqlite:
        # WAL 允许读操作与写操作更好地并行。
        # busy_timeout 让 SQLite 在短时间写锁竞争时自动等待。
        with engine.begin() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL"))
            connection.execute(text("PRAGMA synchronous=NORMAL"))
            connection.execute(text("PRAGMA busy_timeout=30000"))
    # 学习项目暂未引入 Alembic，启动时通过 create_all 创建缺失的数据表。
    # 注意：create_all 不会修改已存在表的结构，后续字段变更仍需要迁移工具。
    Base.metadata.create_all(bind=engine)


configure_engine()
