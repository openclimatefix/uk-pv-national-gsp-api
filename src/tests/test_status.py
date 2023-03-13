""" Test for main app """
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from nowcasting_datamodel.models import Status, ForecastSQL

from freezegun import freeze_time

from database import get_session
from main import app

client = TestClient(app)


def test_read_latest_status(db_session):
    """Check main GB/pv/status route works"""
    status = Status(message="Good", status="ok").to_orm()
    db_session.add(status)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/status")
    assert response.status_code == 200

    returned_status = Status(**response.json())
    assert returned_status.message == status.message
    assert returned_status.status == status.status


@freeze_time("2023-01-01")
def test_check_last_forecast_run_no_forecast(db_session):
    """Check main check_last_forecast_run fales where there are not forecasts"""
    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run")
    assert response.status_code == 404


@freeze_time("2023-01-02")
def test_check_last_forecast_run_correct(db_session):
    """Check check_last_forecast_run works fine"""
    forecast_creation_time = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    forecast = ForecastSQL(forecast_creation_time=forecast_creation_time)
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run")
    assert response.status_code == 200


@freeze_time("2023-01-03")
def test_check_last_forecast_error(db_session):
    """Check check_last_forecast_run works fine"""
    forecast_creation_time = datetime.now(tz=timezone.utc) - timedelta(hours=3)
    forecast = ForecastSQL(forecast_creation_time=forecast_creation_time)
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run")
    assert response.status_code == 404
