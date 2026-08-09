"""Pytest fixtures for ITBIS.

Tests run against a dedicated PostgreSQL database (``itbis_test``) so the
development data is never touched. The app's ``Settings`` reads environment
variables first, so we set ``DATABASE_URL`` before importing any app module.
"""

import os
import sys
from pathlib import Path

# Must be set BEFORE importing app modules
os.environ["DATABASE_URL"] = (
    os.environ.get("TEST_DATABASE_URL")
    or "postgresql://itbis_user:changeme@localhost:5433/itbis_test"
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-pytest"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.base import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _create_test_db() -> None:
    """Create the itbis_test database if it does not exist yet."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    url = os.environ["DATABASE_URL"]
    parts = url.split("@")[-1].split("/")
    host_port = parts[0]
    dbname = parts[1]
    host, port = host_port.split(":")
    # connect to the "postgres" maintenance DB
    conn = psycopg2.connect(
        host=host, port=port, user="itbis_user", password="changeme", dbname="itbis_db"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{dbname}'")
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{dbname}"')
    cur.close()
    conn.close()


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    _create_test_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # tear down the test schema so re-runs start clean
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Delete all rows after each test (reverse FK order)."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
            conn.execute(
                text(f"ALTER SEQUENCE IF EXISTS {table.name}_id_seq RESTART WITH 1")
            )


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """TestClient with the dependency override pointed at the test DB."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Register an analyst and return Bearer headers for authenticated calls."""

    def _auth(email: str = "analyst@test.com", password: str = "test1234",
              role: str = "security_analyst", full_name: str = "Test Analyst"):
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name, "role": role},
        )
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth
