from sqlalchemy import create_engine, inspect, text

from app import database


def test_sqlite_compatibility_migration_is_idempotent(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE devices ("
                "id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, "
                "stream_id VARCHAR(100) NOT NULL, enabled BOOLEAN NOT NULL)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE records ("
                "id INTEGER PRIMARY KEY, file_path VARCHAR(500) NOT NULL)"
            )
        )
        connection.execute(
            text("CREATE TABLE experiments (id INTEGER PRIMARY KEY, name VARCHAR(120))")
        )

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database.settings, "database_url", f"sqlite:///{db_path}")

    database._migrate_sqlite_schema()
    database._migrate_sqlite_schema()

    inspector = inspect(engine)
    device_columns = {column["name"] for column in inspector.get_columns("devices")}
    record_indexes = inspector.get_indexes("records")
    experiment_columns = {
        column["name"] for column in inspector.get_columns("experiments")
    }

    assert "is_online" in device_columns
    assert any(
        index.get("unique") and index.get("column_names") == ["file_path"]
        for index in record_indexes
    )
    assert {
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "sample_count",
        "measurement_method",
    }.issubset(experiment_columns)
