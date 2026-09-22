from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.app.main import app
from services.common.db import Base, get_db, make_engine, make_session_factory

# Test databases live in a repository-local scratch directory instead of the
# operating-system temp directory. That keeps test runs reproducible on hosts
# where the OS temp location is locked down, and it makes leaked test
# databases easy to find and delete.
TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".pytest_tmp"


@pytest.fixture()
def tmp_dir() -> Iterator[Path]:
    path = TEST_TMP_ROOT / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def db_session(tmp_dir):
    database_url = f"sqlite:///{tmp_dir / 'test.db'}"
    engine = make_engine(database_url)
    testing_session_factory = make_session_factory(engine)

    Base.metadata.create_all(bind=engine)
    session = testing_session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
