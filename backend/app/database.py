from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
engine_options = (
    {"pool_size": 20, "max_overflow": 20, "pool_timeout": 30}
    if is_sqlite
    else {}
)
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **engine_options,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import alert, device, experiment, record  # noqa: F401

    if is_sqlite:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL"))
            connection.execute(text("PRAGMA synchronous=NORMAL"))
            connection.execute(text("PRAGMA busy_timeout=30000"))
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema() -> None:
    """Apply the two idempotency-related migrations used by this prototype.

    A production deployment should replace this small compatibility bridge
    with Alembic. Keeping it here allows existing project databases to start
    after adding Hook state and record uniqueness.
    """
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "devices" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("devices")}
        if "is_online" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE devices "
                        "ADD COLUMN is_online BOOLEAN NOT NULL DEFAULT 0"
                    )
                )

    inspector = inspect(engine)
    if "records" in inspector.get_table_names():
        has_unique_file_path = any(
            index.get("unique") and index.get("column_names") == ["file_path"]
            for index in inspector.get_indexes("records")
        )
        if not has_unique_file_path:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS "
                        "ux_records_file_path ON records(file_path)"
                    )
                )

    inspector = inspect(engine)
    if "experiments" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("experiments")}
        additions = {
            "p50_latency_ms": "FLOAT",
            "p95_latency_ms": "FLOAT",
            "p99_latency_ms": "FLOAT",
            "sample_count": "INTEGER NOT NULL DEFAULT 0",
            "measurement_method": "VARCHAR(100)",
        }
        with engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(
                        text(f"ALTER TABLE experiments ADD COLUMN {name} {sql_type}")
                    )
