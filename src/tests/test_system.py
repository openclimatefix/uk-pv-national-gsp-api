""" Test for main app """
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from freezegun import freeze_time
from nowcasting_datamodel.fake import (
    make_fake_forecast,
    make_fake_forecasts,
    make_fake_national_forecast,
)
from nowcasting_datamodel.models import (
    Forecast,
    ForecastValue,
    ForecastValueLatestSQL,
    GSPYield,
    Location,
    LocationSQL,
    ManyForecasts,
)
from nowcasting_datamodel.update import update_all_forecast_latest

from database import get_session
from main import app

client = TestClient(app)



def test_get_gsp_systems(db_session):
    """Check main system/GB/gsp/ works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("v0/system/GB/gsp/")
    assert response.status_code == 200

    locations = [Location(**location) for location in response.json()]
    assert len(locations) == 10


def test_gsp_boundaries(db_session):
    """Check main system/GB/gsp/boundaries"""

# for the moment, this code doesn't seem right, 
# it's the test for getting the national forecast 
# I updated the route in the test though 
    forecast = make_fake_national_forecast(session=db_session)
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/system/GB/gsp/boundaries")
    assert response.status_code == 200
    assert len(response.json()) > 0


