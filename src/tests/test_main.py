""" Test for main app """

from fastapi.testclient import TestClient

from main import Forecast, ManyForecasts, app, version

client = TestClient(app)


def test_read_main():
    """Check main route works"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == version


def test_read_latest_gsp():
    """Check main GB/pv/gsp/{gsp_id} route works"""
    response = client.get("/v0/forecasts/GB/pv/gsp/1")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_read_latest():
    """Check main GB/pv/gsp route works"""
    response = client.get("/v0/forecasts/GB/pv/gsp")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10


def test_read_latest_national():
    """Check main GB/pv/national route works"""
    response = client.get("/v0/forecasts/GB/pv/national")
    assert response.status_code == 200

    _ = Forecast(**response.json())


