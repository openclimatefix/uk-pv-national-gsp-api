""" Pytest fixtures for tests """

import os

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.fake import make_fake_forecasts
from nowcasting_datamodel.models.base import Base_PV

from nowcasting_api.auth_utils import get_auth_implicit_scheme, get_user
from nowcasting_api.database import get_session
from nowcasting_api.main import app


@pytest.fixture
def forecasts(db_session):
    """Pytest fixture of 338 fake forecasts"""
    f = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(f)
    return f


@pytest.fixture
def db_connection():
    """Pytest fixture for a database connection"""
    url = os.environ["DB_URL"]
    connection = DatabaseConnection(url=url, echo=False)
    connection.create_all()
    Base_PV.metadata.create_all(connection.engine)

    yield connection

    connection.drop_all()
    Base_PV.metadata.drop_all(connection.engine)


@pytest.fixture(scope="function", autouse=True)
def db_session(db_connection):
    """Creates a new database session for a test."""
    connection = db_connection.engine.connect()
    t = connection.begin()

    with db_connection.get_session() as s:
        s.begin()
        yield s
        s.rollback()

        t.rollback()
        connection.close()


@pytest.fixture()
def api_client(db_session):
    """Get API test client

    We override the user and the database session
    """
    from nowcasting_api.cache import setup_cache

    setup_cache()

    from nowcasting_api.cache import setup_cache

    setup_cache()

    client = TestClient(app)

    app.dependency_overrides[get_auth_implicit_scheme] = lambda: None
    app.dependency_overrides[get_user] = lambda: None
    app.dependency_overrides[get_session] = lambda: db_session

    return client


@pytest_asyncio.fixture
async def async_client(db_session):
    """Get async API test client for async tests

    We override the user and the database session
    """
    from nowcasting_api.cache import setup_cache

    setup_cache()

    app.dependency_overrides[get_auth_implicit_scheme] = lambda: None
    app.dependency_overrides[get_user] = lambda: None
    app.dependency_overrides[get_session] = lambda: db_session

    # Using ASGITransport to route requests directly to the FastAPI app
    transport = httpx.ASGITransport(app=app)

    # Create AsyncClient with the transport
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
