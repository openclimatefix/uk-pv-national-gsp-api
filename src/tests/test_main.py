""" Test for main app """

from fastapi.testclient import TestClient
from nowcasting_forecast.database.models import Forecast, ManyForecasts
from nowcasting_forecast.database.fake import make_fake_forecasts

from main import app, get_session, version

client = TestClient(app)


def test_read_main():
    """Check main route works"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == version


def test_read_latest_one_gsp(db_session):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)))
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/forecasts/GB/pv/gsp/1")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_read_latest_all_gsp(db_session):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 338)))
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/forecasts/GB/pv/gsp")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 338


def test_read_latest_national():
    """Check main GB/pv/national route works"""
    response = client.get("/v0/forecasts/GB/pv/national")
    assert response.status_code == 200

    _ = Forecast(**response.json())
