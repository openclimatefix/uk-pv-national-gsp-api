""" Test for main app """
from datetime import datetime, timezone

from freezegun import freeze_time
from nowcasting_datamodel.fake import make_fake_forecasts
from nowcasting_datamodel.models import (
    Forecast,
    GSPYield,
    Location,
    LocationSQL,
    LocationWithGSPYields,
    ManyForecasts,
)
from nowcasting_datamodel.save.update import update_all_forecast_latest

from database import get_session
from main import app


@freeze_time("2022-01-01")
def test_read_latest_one_gsp(db_session, api_client):
    """Check main solar/GB/gsp/forecast/{gsp_id} route works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/1")

    assert response.status_code == 200

    _ = Forecast(**response.json())


def test_read_latest_all_gsp(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=False")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert len(r.forecasts[0].forecast_values) == 112


def test_read_latest_all_gsp_normalized(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all normalized route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.add_all(forecasts)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=False&normalize=True")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 13000
    assert r.forecasts[1].forecast_values[0].expected_power_generation_megawatts <= 10


def test_read_latest_all_gsp_historic(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all historic route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
        historic=True,
    )
    db_session.add_all(forecasts)
    update_all_forecast_latest(forecasts=forecasts, session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=True")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())

    assert len(r.forecasts) == 11
    assert len(r.forecasts[0].forecast_values) > 50
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 13000
    assert r.forecasts[1].forecast_values[0].expected_power_generation_megawatts <= 10


@freeze_time("2022-01-01")
def test_read_truths_for_a_specific_gsp(db_session, api_client):
    """Check main solar/GB/gsp/pvlive route works"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=122, label="GSP_122", status_interval_minutes=5
    ).to_orm()

    # add pv system to yield object
    gsp_yield_1_sql.location = gsp_sql_1
    gsp_yield_2_sql.location = gsp_sql_1
    gsp_yield_3_sql.location = gsp_sql_1

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_sql_1])

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/pvlive/122")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 3

    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]


@freeze_time("2022-01-01")
def test_read_truths_for_all_gsp(db_session, api_client):
    """Check main solar/GB/gsp/pvlive/all route works"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=122, label="GSP_122", status_interval_minutes=5
    ).to_orm()
    gsp_sql_2: LocationSQL = Location(
        gsp_id=123, label="GSP_123", status_interval_minutes=10
    ).to_orm()

    # add pv system to yield object
    gsp_yield_1_sql.location = gsp_sql_1
    gsp_yield_2_sql.location = gsp_sql_1
    gsp_yield_3_sql.location = gsp_sql_2

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_sql_1, gsp_sql_2])

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/pvlive/all")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 2

    location = [LocationWithGSPYields(**location) for location in r_json]
    assert len(location) == 2
    assert len(location[0].gsp_yields) == 2
