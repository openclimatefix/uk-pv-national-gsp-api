from datetime import datetime

from fastapi.testclient import TestClient

from main import MultipleGSP, app, _floor_30_minutes_dt, version
from tests.test_utils import get_every_minute

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == version


def test_read_latest():
    response = client.get("/v0/latest")
    assert response.status_code == 200

    r = MultipleGSP(**response.json())
    assert len(r.gsps) == 339


def test_floor_30_minutes():
    """
    Test if floor_30_minutes_dt method works by testing against every minute in a hour
    For minutes in range [0, 30) => Will floor to 0 minutes
    For minutes in range [30, 60) => Will floor to 30 minutes
    """
    list_of_time = get_every_minute()
    input = datetime.fromisoformat("2021-09-30 12:15:05")
    expected_output = datetime.fromisoformat("2021-09-30 12:00:00")

    assert _floor_30_minutes_dt(input) == expected_output  # Basic control test

    for time in list_of_time:
        floor_minute = _floor_30_minutes_dt(time)
        if time.minute < 30:
            assert floor_minute.minute == 0
        else:
            assert floor_minute.minute == 30
