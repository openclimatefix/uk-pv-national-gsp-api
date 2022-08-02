""" Pytest fixitures for tests """
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.fake import make_fake_forecasts
from nowcasting_datamodel.models.base import Base_Forecast, Base_PV

from auth_utils import get_auth_implicit_scheme, get_user
from database import get_session
from main import app


@pytest.fixture
def forecasts(db_session):
    """Pytest fixture of 338 fake forecasts"""
    # create
    f = make_fake_forecasts(gsp_ids=list(range(0, 338)), session=db_session)
    db_session.add_all(f)

    return f


@pytest.fixture
def db_connection():
    """Pytest fixture for a database connection"""
    with tempfile.NamedTemporaryFile(suffix="db") as tmp:
        # set url option to not check same thread, this solves an error seen in testing

        url = f"sqlite:///{tmp.name}.db?check_same_thread=False"
        os.environ["DB_URL"] = url
        os.environ["DB_URL_PV"] = url
        connection = DatabaseConnection(url=url)
        Base_Forecast.metadata.create_all(connection.engine)
        Base_PV.metadata.create_all(connection.engine)

        yield connection


@pytest.fixture(scope="function", autouse=True)
def db_session(db_connection):
    """Creates a new database session for a test."""

    with db_connection.get_session() as s:
        s.begin()
        yield s

        s.rollback()


@pytest.fixture()
def api_client(db_session):
    """Get API test client

    We override the user and the database session
    """
    client = TestClient(app)

    app.dependency_overrides[get_auth_implicit_scheme] = lambda: None
    app.dependency_overrides[get_user] = lambda: None
    app.dependency_overrides[get_session] = lambda: db_session

    return client
