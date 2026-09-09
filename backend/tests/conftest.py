from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.database import configure_engine
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    configure_engine(f"sqlite:///{tmp_path}/llvp.db")
    with TestClient(create_app()) as test_client:
        yield test_client
