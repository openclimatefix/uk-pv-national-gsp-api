""" Test for main app """
from datetime import datetime

from fastapi.testclient import TestClient
from nowcasting_datamodel.fake import make_fake_forecasts, make_fake_national_forecast
from nowcasting_datamodel.models import Forecast, GSPYield, Location, LocationSQL, ManyForecasts

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


def test_read_truth_one_gsp(db_session):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_sql_1: LocationSQL = Location(gsp_id=1, label="GSP_1", status_interval_minutes=5).to_orm()
    gsp_sql_2: LocationSQL = Location(gsp_id=2, label="GSP_2", status_interval_minutes=5).to_orm()

    # add pv system to yield object
    gsp_yield_1_sql.location = gsp_sql_1
    gsp_yield_2_sql.location = gsp_sql_1
    gsp_yield_3_sql.location = gsp_sql_2

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_sql_1, gsp_sql_2])

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/truth/one_gsp/1")
    assert response.status_code == 200

    r_json = response.json()
    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]
