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


@freeze_time("2022-01-01")
def test_read_latest_one_gsp(db_session):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/gsp/forecast/one_gsp/1")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_read_latest_all_gsp(db_session):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/all")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert len(r.forecasts[0].forecast_values) == 2


def test_read_latest_all_gsp_normalized(db_session):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/all/?normalize=True")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 1


def test_read_latest_all_gsp_historic(db_session):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)
    update_all_forecast_latest(forecasts=forecasts, session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/all/?historic=True")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert len(r.forecasts[0].forecast_values) == 2
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 1


@freeze_time("2022-07-01 10:00:00")
def test_read_latest_all_gsp_forecast_horizon(db_session):
    """Check main GB/pv/gsp route works"""

    t0_datetime_utc = datetime(2022, 7, 1, 12, tzinfo=timezone.utc)
    created_utc = datetime(2022, 7, 1, 10, tzinfo=timezone.utc)

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=t0_datetime_utc,
    )
    forecasts[0].forecast_values[0].created_utc = created_utc
    forecasts[0].forecast_values[1].created_utc = created_utc
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    # no forecast are made 3 horus before target time
    response = client.get("/v0/GB/solar/gsp/forecast/latest/0?forecast_horizon_minutes=180")
    assert response.status_code == 200

    r = [ForecastValue(**f) for f in response.json()]

    # print(r.forecasts[0].forecast_values[0].created_utc)
    assert len(r) == 0

    response = client.get("/v0/GB/solar/gsp/forecast/latest/0?forecast_horizon_minutes=119")
    assert response.status_code == 200

    r = [ForecastValue(**f) for f in response.json()]
    assert len(r) == 2


@freeze_time("2022-06-01")
def test_read_forecast_one_gsp(db_session):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    forecast_value_1_sql = ForecastValueLatestSQL(
        target_time=datetime(2022, 6, 2), expected_power_generation_megawatts=1, gsp_id=1
    )

    forecast_value_2_sql = ForecastValueLatestSQL(
        target_time=datetime(2022, 6, 1, 1), expected_power_generation_megawatts=2, gsp_id=1
    )

    forecast_value_3_sql = ForecastValueLatestSQL(
        target_time=datetime(2022, 6, 1), expected_power_generation_megawatts=3, gsp_id=1
    )

    forecast = make_fake_forecast(
        gsp_id=1, session=db_session, t0_datetime_utc=datetime(2020, 1, 1)
    )
    forecast.forecast_values_latest.append(forecast_value_1_sql)
    forecast.forecast_values_latest.append(forecast_value_2_sql)
    forecast.forecast_values_latest.append(forecast_value_3_sql)

    # add to database
    db_session.add_all([forecast])

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/forecast/latest/1")
    assert response.status_code == 200

    r_json = response.json()
    # no forecast are from 'make_fake_forecast', as these are for 2020
    # the two are 'forecast_value_1' and 'forecast_value_3'
    # 'forecast_value_2' is not included as it has the same target time as
    # 'forecast_value_3'
    for i in r_json:
        print(i)
    assert len(r_json) == 3
    _ = [ForecastValue(**forecast_value) for forecast_value in r_json]
