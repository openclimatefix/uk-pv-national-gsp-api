""" Pytest fixitures for tests """
import os
import tempfile

import pytest
from nowcasting_forecast.database.connection import DatabaseConnection
from nowcasting_forecast.database.fake import make_fake_forecasts
from nowcasting_forecast.database.models import Base


@pytest.fixture
def forecasts(db_session):
    """Pytest fixture of 338 fake forecasts"""
    # create
    f = make_fake_forecasts(gsp_ids=list(range(0, 338)))
    db_session.add_all(f)

    return f


@pytest.fixture
def db_connection():
    """Pytest fixture for a database connection"""
    with tempfile.NamedTemporaryFile(suffix="db") as tmp:
        # set url option to not check same thread, this solves an error seen in testing
        url = f"sqlite:///{tmp.name}.db?check_same_thread=False"
        os.environ["DB_URL"] = url
        connection = DatabaseConnection(url=url)
        Base.metadata.create_all(connection.engine)

        yield connection


@pytest.fixture(scope="function", autouse=True)
def db_session(db_connection):
    """Creates a new database session for a test."""

    with db_connection.get_session() as s:
        s.begin()
        yield s

        s.rollback()
