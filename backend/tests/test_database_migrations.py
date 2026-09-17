from sqlalchemy import inspect

import app.database as database


def test_initial_migration_creates_video_sources_table(tmp_path) -> None:
    database.configure_engine(f"sqlite:///{tmp_path}/migration.db")

    database.run_migrations()

    table_names = inspect(database.engine).get_table_names()
    assert "video_sources" in table_names
    assert "alembic_version" in table_names
