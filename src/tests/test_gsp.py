""" Test for main app """
from datetime import datetime, timezone

from freezegun import freeze_time
from nowcasting_datamodel.fake import (
    make_fake_forecast,
    make_fake_forecasts,
    make_fake_national_forecast,
)
from nowcasting_datamodel.models import (
    Forecast,
    ForecastValue,
    GSPYield,
    Location,
    LocationSQL,
    ManyForecasts,
)
from nowcasting_datamodel.update import update_all_forecast_latest

from database import get_session
from main import app


@freeze_time("2022-01-01")
def test_read_latest_one_gsp(db_session, api_client):

    """Check main GB/pv/gsp/{gsp_id} route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    response = api_client.get("/v0/GB/solar/gsp/forecast/one_gsp/1")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_read_latest_all_gsp(db_session, api_client):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/GB/solar/gsp/forecast/all")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert len(r.forecasts[0].forecast_values) == 2


def test_read_latest_all_gsp_normalized(db_session, api_client):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/GB/solar/gsp/forecast/all/?normalize=True")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 1


def test_read_latest_all_gsp_historic(db_session, api_client):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)
    update_all_forecast_latest(forecasts=forecasts, session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/GB/solar/gsp/forecast/all/?historic=True")
    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert len(r.forecasts[0].forecast_values) == 2
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 1


def test_read_latest_national(db_session, api_client):
    """Check main GB/pv/national route works"""

    forecast = make_fake_national_forecast(session=db_session)
    db_session.add(forecast)

    response = api_client.get("/v0/GB/solar/gsp/forecast/national")
    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_gsp_boundaries(db_session, api_client):
    """Check main GB/pv/national route works"""

    forecast = make_fake_national_forecast(session=db_session)
    db_session.add(forecast)

    response = api_client.get("/v0/GB/solar/gsp/gsp_boundaries")
    assert response.status_code == 200
    assert len(response.json()) > 0


@freeze_time("2022-01-01")
def test_read_truth_one_gsp(db_session, api_client):
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
    response = api_client.get("/v0/GB/solar/gsp/pvlive/one_gsp/1")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 2
    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]


@freeze_time("2022-06-01")
def test_read_forecast_one_gsp(db_session, api_client):
    """Check main GB/pv/gsp/{gsp_id} route works"""

    forecast_value_1 = ForecastValue(
        target_time=datetime(2022, 6, 2), expected_power_generation_megawatts=1
    )
    forecast_value_1_sql = forecast_value_1.to_orm()

    forecast_value_2 = ForecastValue(
        target_time=datetime(2022, 6, 1, 1), expected_power_generation_megawatts=2
    )
    forecast_value_2_sql = forecast_value_2.to_orm()

    forecast_value_3 = ForecastValue(
        target_time=datetime(2022, 6, 1), expected_power_generation_megawatts=3
    )
    forecast_value_3_sql = forecast_value_3.to_orm()

    forecast = make_fake_forecast(
        gsp_id=1, session=db_session, t0_datetime_utc=datetime(2020, 1, 1)
    )
    forecast.forecast_values.append(forecast_value_1_sql)
    forecast.forecast_values.append(forecast_value_2_sql)
    forecast.forecast_values.append(forecast_value_3_sql)

    # add to database
    db_session.add_all([forecast])

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/GB/solar/gsp/forecast/latest/1")
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


def test_get_gsp_systems(db_session, api_client):
    """Check main GB/pv/gsp route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("v0/GB/solar/gsp/gsp_systems")
    assert response.status_code == 200

    locations = [Location(**location) for location in response.json()]
    assert len(locations) == 10
