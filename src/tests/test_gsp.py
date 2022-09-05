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

    response = client.get("/v0/GB/solar/forecast/1")
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

    response = client.get("/v0/GB/solar/forecast/all")
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

    response = client.get("/v0/GB/solar/forecast/all/?normalize=True")
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

    response = client.get("/v0/GB/solar/forecast/all/?historic=True")
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
    response = client.get("/v0/GB/solar/forecast/forecast_values/0?forecast_horizon_minutes=180")
    assert response.status_code == 200

    r = [ForecastValue(**f) for f in response.json()]

    # print(r.forecasts[0].forecast_values[0].created_utc)
    assert len(r) == 0

    response = client.get("/v0/GB/solar/forecast/forecast_values/0?forecast_horizon_minutes=119")
    assert response.status_code == 200

    r = [ForecastValue(**f) for f in response.json()]
    assert len(r) == 2


def test_read_latest_national(db_session):
    """Check main GB/pv/national route works"""

    forecast = make_fake_national_forecast(session=db_session)
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/forecast/national")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_gsp_boundaries(db_session):
    """Check main GB/pv/national route works"""

    forecast = make_fake_national_forecast(session=db_session)
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/GB/solar/gsp/gsp_boundaries")
    assert response.status_code == 200
    assert len(response.json()) > 0


@freeze_time("2022-01-01")
def test_read_truth_one_gsp(db_session):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=3)
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

    response = client.get("/v0/GB/solar/pvlive/1")
    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 2
    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]


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

    response = client.get("/v0/GB/solar/forecast/forecast_values/1")
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


def test_get_gsp_systems(db_session):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("v0/GB/solar/gsp/gsp_systems")
    assert response.status_code == 200

    locations = [Location(**location) for location in response.json()]
    assert len(locations) == 10
