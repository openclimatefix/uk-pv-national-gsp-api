""" Test for main app """

from datetime import UTC, datetime, timezone

from freezegun import freeze_time
from nowcasting_datamodel.fake import make_fake_forecasts
from nowcasting_datamodel.models import (
    ForecastValue,
    ForecastValueSevenDaysSQL,
    GSPYield,
    Location,
    LocationSQL,
    LocationWithGSPYields,
    ManyForecasts,
)
from nowcasting_datamodel.read.read_models import get_model
from nowcasting_datamodel.save.save import save_all_forecast_values_seven_days
from nowcasting_datamodel.save.update import update_all_forecast_latest

from nowcasting_api.database import get_session
from nowcasting_api.main import app
from nowcasting_api.pydantic_models import GSPYieldGroupByDatetime, OneDatetimeManyForecastValues
from nowcasting_api.utils import N_SLOW_CALLS_PER_MINUTE, floor_30_minutes_dt


@freeze_time("2022-01-01")
def test_read_latest_one_gsp(db_session, api_client):
    """Check main solar/GB/gsp/{gsp_id}/forecast route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 2)), session=db_session, add_latest=True, model_name="blend"
    )
    db_session.add_all(forecasts)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/1/forecast")

    assert response.status_code == 200

    _ = [ForecastValue(**f) for f in response.json()]


@freeze_time("2022-01-01")
def test_read_latest_one_gsp_national(db_session, api_client):
    """Check main solar/GB/gsp/{gsp_id}/forecast route works"""

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 2)), session=db_session, add_latest=True, model_name="blend"
    )
    db_session.add_all(forecasts)
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/0/forecast")

    assert response.status_code == 200

    _ = [ForecastValue(**f) for f in response.json()]


def test_read_latest_one_gsp_filter_creation_utc(db_session, api_client):
    """Check main solar/GB/gsp/{gsp_id}/forecast route works"""

    with freeze_time("2022-01-01"):
        forecasts = make_fake_forecasts(
            gsp_ids=list(range(0, 2)), session=db_session, model_name="blend", n_fake_forecasts=10
        )
        db_session.add_all(forecasts)
        db_session.commit()
        save_all_forecast_values_seven_days(forecasts=forecasts, session=db_session)

    with freeze_time("2022-01-02"):
        forecasts_2 = make_fake_forecasts(
            gsp_ids=list(range(0, 2)), session=db_session, model_name="blend", n_fake_forecasts=10
        )
        db_session.add_all(forecasts_2)
        db_session.commit()
        save_all_forecast_values_seven_days(forecasts=forecasts_2, session=db_session)
        assert len(db_session.query(ForecastValueSevenDaysSQL).all()) == 2 * 2 * 10

    with freeze_time("2022-01-03"):
        app.dependency_overrides[get_session] = lambda: db_session

        response = api_client.get("/v0/solar/GB/gsp/1/forecast?creation_limit_utc=2022-01-02")

        assert response.status_code == 200

        f = [ForecastValue(**f) for f in response.json()]
        assert len(f) == 10
        assert f[0].target_time == forecasts[1].forecast_values[0].target_time


def test_read_latest_all_gsp(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all route works"""

    _ = get_model(session=db_session, name="blend", version="0.0.1")

    _ = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        model_name="blend",
        session=db_session,
        add_latest=True,
        t0_datetime_utc=floor_30_minutes_dt(datetime.now(tz=UTC)),
    )

    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=False")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert len(r.forecasts[0].forecast_values) == 16


def test_read_latest_all_gsp_filter_gsp(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all route works"""

    _ = get_model(session=db_session, name="blend", version="0.0.1")

    _ = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        model_name="blend",
        session=db_session,
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )

    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=False&gsp_ids=1,2,3")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 3
    assert len(r.forecasts[0].forecast_values) == 16


def test_read_latest_gsp_id_greater_than_total(db_session, api_client):
    """Check that request with gsp_id>=318 returns 204"""

    gsp_id = 318
    response = api_client.get(f"/v0/solar/GB/gsp/forecast/{gsp_id}/?historic=False&normalize=True")

    assert response.status_code == 204


def test_read_latest_gsp_id_equal_to_total(db_session, api_client):
    """Check that request with gsp_id<318 returns 200"""

    _ = make_fake_forecasts(gsp_ids=[317], session=db_session, add_latest=True, model_name="blend")
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/317")

    assert response.status_code == 200

    _ = [ForecastValue(**f) for f in response.json()]


def test_read_latest_all_gsp_normalized(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all normalized route works"""

    _ = get_model(session=db_session, name="blend", version="0.0.1")

    _ = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        model_name="blend",
        t0_datetime_utc=datetime.now(tz=timezone.utc),
    )
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=False&normalize=True")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())
    assert len(r.forecasts) == 10
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 13000
    assert r.forecasts[1].forecast_values[0].expected_power_generation_megawatts <= 40


def test_read_latest_all_gsp_historic(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all historic route works"""

    _ = get_model(session=db_session, name="blend", version="0.0.1")

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        model_name="blend",
        t0_datetime_utc=datetime.now(tz=timezone.utc),
        historic=True,
    )
    db_session.commit()
    update_all_forecast_latest(forecasts=forecasts, session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=True")

    assert response.status_code == 200

    r = ManyForecasts(**response.json())

    assert len(r.forecasts) == 9  # dont get national
    assert len(r.forecasts[0].forecast_values) == 16
    assert r.forecasts[0].forecast_values[0].expected_power_generation_megawatts <= 13000
    assert r.forecasts[1].forecast_values[0].expected_power_generation_megawatts <= 40


def test_read_latest_all_gsp_historic_compact(db_session, api_client):
    """Check main solar/GB/gsp/forecast/all historic route works"""

    _ = get_model(session=db_session, name="blend", version="0.0.1")

    forecasts = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        session=db_session,
        model_name="blend",
        t0_datetime_utc=datetime.now(tz=timezone.utc),
        historic=True,
    )
    db_session.commit()
    update_all_forecast_latest(forecasts=forecasts, session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=True&compact=True")

    assert response.status_code == 200

    r = [OneDatetimeManyForecastValues(**f) for f in response.json()]

    assert len(r) == 16
    assert len(r[0].forecast_values) == 9  # dont get the national
    assert r[0].forecast_values[1] <= 13000


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
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/pvlive/122")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 3

    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]


def test_read_pvlive_for_gsp_id_over_total(db_session, api_client):
    """Check solar/GB/gsp/pvlive returns 204 when gsp_id over total"""

    gsp_id = 318
    response = api_client.get(f"/v0/solar/GB/gsp/pvlive/{gsp_id}")

    assert response.status_code == 204


@freeze_time("2022-01-01")
def test_read_truths_for_gsp_id_less_than_total(db_session, api_client):
    """Check solar/GB/gsp/pvlive returns 200 when gsp_id under total"""

    gsp_yield = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_sql = gsp_yield.to_orm()

    gsp_id = 317
    gsp_sql: LocationSQL = Location(
        gsp_id=gsp_id, label="GSP_317", status_interval_minutes=1
    ).to_orm()

    # add pv system to yield object
    gsp_yield_sql.location = gsp_sql

    # add to database
    db_session.add_all([gsp_yield_sql, gsp_sql])
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get(f"/v0/solar/GB/gsp/pvlive/{gsp_id}")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 1

    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]


def setup_gsp_yield_data(db_session):
    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_yield_4 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_4_sql = gsp_yield_4.to_orm()

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
    gsp_yield_4_sql.location = gsp_sql_1

    # add to database
    db_session.add_all(
        [gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_yield_4_sql, gsp_sql_1, gsp_sql_2]
    )
    db_session.commit()


@freeze_time("2022-01-01")
def test_read_truths_for_all_gsp(db_session, api_client):
    """Check main solar/GB/gsp/pvlive/all route works"""

    setup_gsp_yield_data(db_session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/pvlive/all")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 2

    location = [LocationWithGSPYields(**location) for location in r_json]
    assert len(location) == 2
    assert len(location[0].gsp_yields) == 3


@freeze_time("2022-01-01")
def test_read_truths_for_all_gsp_filter_gsp(db_session, api_client):
    """Check main solar/GB/gsp/pvlive/all route works"""

    setup_gsp_yield_data(db_session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/pvlive/all?gsp_ids=122")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 1

    location = [LocationWithGSPYields(**location) for location in r_json]
    assert len(location) == 1
    assert len(location[0].gsp_yields) == 3


@freeze_time("2022-01-01")
def test_read_truths_for_all_gsp_compact(db_session, api_client):
    """Check main solar/GB/gsp/pvlive/all route works with compact flag"""

    setup_gsp_yield_data(db_session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/pvlive/all?compact=true")

    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 3

    datetimes_with_gsp_yields = [GSPYieldGroupByDatetime(**location) for location in r_json]
    assert len(datetimes_with_gsp_yields) == 3
    assert len(datetimes_with_gsp_yields[0].generation_kw_by_gsp_id) == 1
    assert len(datetimes_with_gsp_yields[1].generation_kw_by_gsp_id) == 2
    assert len(datetimes_with_gsp_yields[2].generation_kw_by_gsp_id) == 1


def test_slow_rate_limit_exceeded(db_session, api_client):
    """Check a 429 is thrown if the slow rate limit is exceeded"""

    _ = get_model(session=db_session, name="blend", version="0.0.1")

    _ = make_fake_forecasts(
        gsp_ids=list(range(0, 10)),
        model_name="blend",
        session=db_session,
        add_latest=True,
        t0_datetime_utc=floor_30_minutes_dt(datetime.now(tz=UTC)),
    )

    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    # Call gsp/forecast/all/ more times than the rate limit
    responses = [
        api_client.get("/v0/solar/GB/gsp/forecast/all/?historic=False")
        for _ in range(int(N_SLOW_CALLS_PER_MINUTE) + 1)
    ]

    # Check for at least 1 429 - there could be more as this route is called in earlier tests
    assert any(r.status_code == 429 for r in responses)
