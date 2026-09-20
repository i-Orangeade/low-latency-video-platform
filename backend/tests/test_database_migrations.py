from datetime import datetime

from sqlalchemy import inspect, text

import app.database as database


def test_initial_migration_creates_video_sources_table(tmp_path) -> None:
    database.configure_engine(f"sqlite:///{tmp_path}/migration.db")

    database.run_migrations()

    table_names = inspect(database.engine).get_table_names()
    assert "video_sources" in table_names
    assert "alembic_version" in table_names

    columns = {
        column["name"]: column
        for column in inspect(database.engine).get_columns("video_sources")
    }
    assert columns["enabled"]["nullable"] is False
    assert columns["created_at"]["nullable"] is False
    assert columns["updated_at"]["nullable"] is False


def test_metadata_migration_preserves_existing_sources(tmp_path) -> None:
    database.configure_engine(f"sqlite:///{tmp_path}/migration.db")

    with database.engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE video_sources (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    stream_id VARCHAR(100) NOT NULL UNIQUE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO video_sources (id, name, stream_id)
                VALUES (1, 'Existing source', 'existing_001')
                """
            )
        )

    database.run_migrations()

    row = database.engine.connect().execute(
        text(
            """
            SELECT id, name, stream_id, enabled, created_at, updated_at
            FROM video_sources
            WHERE id = 1
            """
        )
    ).one()
    assert row.id == 1
    assert row.name == "Existing source"
    assert row.stream_id == "existing_001"
    assert bool(row.enabled) is True
    assert row.created_at is not None
    assert row.updated_at is not None
    datetime.fromisoformat(str(row.created_at))
    datetime.fromisoformat(str(row.updated_at))
