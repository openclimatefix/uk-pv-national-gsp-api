""" Test for main app """

import os
import tempfile
from datetime import datetime, timedelta, timezone

import fsspec
from fastapi.testclient import TestClient
from freezegun import freeze_time
from nowcasting_datamodel.models import (
    APIRequestSQL,
    ForecastSQL,
    GSPYield,
    InputDataLastUpdatedSQL,
    Location,
    LocationSQL,
    MLModelSQL,
    Status,
    UserSQL,
)

from nowcasting_api.database import get_session
from nowcasting_api.main import app

client = TestClient(app)


def test_read_latest_status(db_session):
    """Check main GB/pv/status route works"""
    status = Status(message="Good", status="ok").to_orm()
    db_session.add(status)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/status")
    assert response.status_code == 200

    returned_status = Status(**response.json())
    assert returned_status.message == status.message
    assert returned_status.status == status.status

    assert len(db_session.query(APIRequestSQL).all()) == 1
    assert len(db_session.query(UserSQL).all()) == 1


@freeze_time("2023-01-01")
def test_check_last_forecast_run_no_forecast(db_session):
    """Check main check_last_forecast_run fales where there are not forecasts"""
    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run")
    assert response.status_code == 404


@freeze_time("2023-01-01")
def test_check_last_forecast_run_no_forecast_model_name(db_session):
    """Check main check_last_forecast_run fales where there are not forecasts"""
    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run?model_name=test")
    assert response.status_code == 404


@freeze_time("2023-01-02")
def test_check_last_forecast_run_correct(db_session):
    """Check check_last_forecast_run works fine"""
    forecast_creation_time = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    forecast = ForecastSQL(forecast_creation_time=forecast_creation_time)
    db_session.add(forecast)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run")
    assert response.status_code == 200


@freeze_time("2023-01-02")
def test_check_last_forecast_run_correct_model_name(db_session):
    """Check check_last_forecast_run works fine with a model name"""
    forecast_creation_time = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    model = MLModelSQL(name="test")
    forecast = ForecastSQL(forecast_creation_time=forecast_creation_time)
    forecast.model = model
    db_session.add(forecast)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run?model_name=test")
    assert response.status_code == 200


@freeze_time("2023-01-02")
def test_check_last_forecast_run_correct_wrong_model_name(db_session):
    """Check check_last_forecast_run gives error due to wrong model name"""
    forecast_creation_time = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
    model = MLModelSQL(name="test")
    forecast = ForecastSQL(forecast_creation_time=forecast_creation_time)
    forecast.model = model
    db_session.add(forecast)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/check_last_forecast_run?model_name=test2")
    assert response.status_code == 404


@freeze_time("2023-01-03")
def test_check_last_forecast_gsp(db_session):
    """Check check_last_forecast_run works fine"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=0, label="national", status_interval_minutes=5
    ).to_orm()
    gsp_yield_1_sql.location = gsp_sql_1

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_sql_1])
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/update_last_data?component=gsp")
    assert response.status_code == 200, response.text

    data = db_session.query(InputDataLastUpdatedSQL).all()
    assert len(data) == 1
    assert data[0].gsp.isoformat() == datetime(2023, 1, 3, tzinfo=timezone.utc).isoformat()

    # check no updates is made, as file modified datetime is the same
    response = client.get("/v0/solar/GB/update_last_data?component=gsp")
    assert response.status_code == 200, response.text
    data = db_session.query(InputDataLastUpdatedSQL).all()
    assert len(data) == 1


def test_check_last_forecast_file(db_session):
    """Check check_last_forecast_run works fine"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=0, label="national", status_interval_minutes=5
    ).to_orm()
    gsp_yield_1_sql.location = gsp_sql_1

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_sql_1])

    app.dependency_overrides[get_session] = lambda: db_session

    # create temp file
    with tempfile.TemporaryDirectory() as tmp:
        filename = os.path.join(tmp, "text.txt")
        with open(filename, "w") as f:
            f.write("test")
        fs = fsspec.open(filename).fs
        modified_date = fs.modified(filename)

        response = client.get(f"/v0/solar/GB/update_last_data?component=nwp&file={filename}")
        assert response.status_code == 200

        data = db_session.query(InputDataLastUpdatedSQL).all()
        assert len(data) == 1
        assert data[0].nwp.isoformat() == modified_date.isoformat()
