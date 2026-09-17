from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = None
SessionLocal = None
is_sqlite = True


class Base(DeclarativeBase):
    pass


def configure_engine(database_url: str | None = None) -> None:
    global engine, SessionLocal, is_sqlite
    url = database_url or settings.database_url
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
    engine = create_engine(url, connect_args=connect_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    if engine is None:
        configure_engine()
    if is_sqlite:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL"))
            connection.execute(text("PRAGMA synchronous=NORMAL"))
            connection.execute(text("PRAGMA busy_timeout=30000"))


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    if engine is None:
        configure_engine()

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


configure_engine()
