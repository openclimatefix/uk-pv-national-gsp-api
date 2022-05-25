""" Test for main app """
from fastapi.testclient import TestClient
from nowcasting_datamodel.models import Status

from database import get_session
from main import app

client = TestClient(app)


def test_read_latest_status(db_session):
    """Check main GB/pv/status route works"""
    status = Status(message="Good", status="ok").to_orm()
    db_session.add(status)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/status")
    assert response.status_code == 200

    _ = Status(**response.json())
