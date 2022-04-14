""" Test for main app """
from fastapi.testclient import TestClient
from nowcasting_datamodel.fake import make_fake_forecasts, make_fake_national_forecast
from nowcasting_datamodel.models import Forecast, ManyForecasts

from database import get_session
from main import app

client = TestClient(app)


def test_read_latest_one_gsp(db_session):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/one_gsp/1")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_read_latest_all_gsp(db_session):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/all")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10


def test_read_latest_national(db_session):
    """Check main GB/pv/national route works"""

    forecast = make_fake_national_forecast()
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/national")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_gsp_boundaries(db_session):
    """Check main GB/pv/national route works"""

    forecast = make_fake_national_forecast()
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/gsp_boundaries")
    assert response.status_code == 200
    assert len(response.json()) > 0
