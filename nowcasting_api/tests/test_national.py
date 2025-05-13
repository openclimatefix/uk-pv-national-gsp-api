""" Test for main app """

from datetime import datetime, timezone

import numpy as np
from freezegun import freeze_time
from nowcasting_datamodel.fake import make_fake_national_forecast
from nowcasting_datamodel.models import GSPYield, Location, LocationSQL
from nowcasting_datamodel.read.read_models import get_model
from nowcasting_datamodel.save.save import save_all_forecast_values_seven_days
from nowcasting_datamodel.save.update import update_all_forecast_latest

from nowcasting_api.database import get_session
from nowcasting_api.main import app
from nowcasting_api.pydantic_models import NationalForecast, NationalForecastValue


def test_read_latest_national_values(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    model = get_model(db_session, name="blend", version="0.0.1")

    forecast = make_fake_national_forecast(
        session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
    )
    forecast.model = model

    assert forecast.forecast_values[0].properties is not None

    db_session.add(forecast)
    update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/national/forecast")
    assert response.status_code == 200

    national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
    assert national_forecast_values[0].plevels is not None
    # index 24 is the middle of the day
    assert (
        national_forecast_values[24].plevels["plevel_10"]
        != national_forecast_values[0].expected_power_generation_megawatts * 0.9
    )
    assert "expected_power_generation_normalized" not in national_forecast_values[0].model_dump()


def test_read_latest_national_values_creation_limit(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    with freeze_time("2023-01-01"):
        model = get_model(db_session, name="blend", version="0.0.1")

        forecast = make_fake_national_forecast(
            session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
        )
        forecast.model = model
        db_session.add(forecast)
        update_all_forecast_latest(forecasts=[forecast], session=db_session)
        save_all_forecast_values_seven_days(forecasts=[forecast], session=db_session)

    with freeze_time("2023-01-02"):
        app.dependency_overrides[get_session] = lambda: db_session

        response = api_client.get("/v0/solar/GB/national/forecast?creation_limit_utc=2023-01-02")
        assert response.status_code == 200

        national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
        assert len(national_forecast_values) == 16

        response = api_client.get("/v0/solar/GB/national/forecast?creation_limit_utc=2022-12-31")
        assert response.status_code == 200

        national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
        assert len(national_forecast_values) == 0


def test_read_latest_national_values_start_and_end_filters(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    with freeze_time("2023-01-01"):
        model = get_model(db_session, name="blend", version="0.0.1")

        forecast = make_fake_national_forecast(
            session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
        )
        forecast.model = model
        db_session.add(forecast)
        update_all_forecast_latest(forecasts=[forecast], session=db_session)

        app.dependency_overrides[get_session] = lambda: db_session

        response = api_client.get("/v0/solar/GB/national/forecast?start_datetime_utc=2023-01-01")
        assert response.status_code == 200

        national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
        assert len(national_forecast_values) == 16

        response = api_client.get(
            "/v0/solar/GB/national/forecast?start_datetime_utc=2023-01-01&end_datetime_utc=2023-01-01 04:00"  # noqa
        )
        assert response.status_code == 200

        national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
        assert len(national_forecast_values) == 9


@freeze_time("2024-01-01")
def test_get_national_forecast(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    model = get_model(db_session, name="blend", version="0.0.1")

    forecast = make_fake_national_forecast(
        session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
    )
    forecast.model = model

    assert forecast.forecast_values[0].properties is not None

    db_session.add(forecast)
    update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/national/forecast?include_metadata=true")
    assert response.status_code == 200

    national_forecast = NationalForecast(**response.json())
    assert national_forecast.forecast_values[0].plevels is not None
    # index 24 is the middle of the day
    assert (
        national_forecast.forecast_values[24].plevels["plevel_10"]
        != national_forecast.forecast_values[0].expected_power_generation_megawatts * 0.9
    )


@freeze_time("2024-01-01")
def test_get_national_forecast_no_init(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    model = get_model(db_session, name="blend", version="0.0.1")

    forecast = make_fake_national_forecast(
        session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
    )
    forecast.model = model
    forecast.initialization_datetime_utc = None

    assert forecast.forecast_values[0].properties is not None

    db_session.add(forecast)
    update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/national/forecast?include_metadata=true")
    assert response.status_code == 200


def test_read_latest_national_values_start_and_end_filters_inculde_metadata(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    with freeze_time("2023-01-01"):
        model = get_model(db_session, name="blend", version="0.0.1")

        forecast = make_fake_national_forecast(
            session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
        )
        forecast.model = model
        db_session.add(forecast)
        update_all_forecast_latest(forecasts=[forecast], session=db_session)

        app.dependency_overrides[get_session] = lambda: db_session

        response = api_client.get(
            "/v0/solar/GB/national/forecast?start_datetime_utc=2023-01-01&include_metadata=true"
        )  # noqa
        assert response.status_code == 200

        national_forecast = NationalForecast(**response.json())
        assert len(national_forecast.forecast_values) == 16

        response = api_client.get(
            "/v0/solar/GB/national/forecast?start_datetime_utc=2023-01-01&end_datetime_utc=2023-01-01 04:00&include_metadata=true"  # noqa
        )
        assert response.status_code == 200

        national_forecast = NationalForecast(**response.json())
        assert len(national_forecast.forecast_values) == 9


def test_get_national_forecast_error(db_session, api_client):
    """Check main solar/GB/national/forecast route works"""

    model = get_model(db_session, name="blend", version="0.0.1")

    forecast = make_fake_national_forecast(
        session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
    )
    forecast.model = model

    assert forecast.forecast_values[0].properties is not None

    db_session.add(forecast)
    update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get(
        "/v0/solar/GB/national/forecast?include_metadata=true&forecast_horizon_minutes=60"
    )
    assert response.status_code == 404


def test_read_latest_national_values_properties(db_session, api_client):
    """Check main solar/GB/national/forecast route works

    Check fake propreties are made
    """

    model = get_model(db_session, name="blend", version="0.0.1")

    forecast = make_fake_national_forecast(
        session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
    )
    forecast.model = model

    db_session.add(forecast)
    update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    # add test=test2 makes sure the cache is not used
    response = api_client.get("/v0/solar/GB/national/forecast?test=test2")
    assert response.status_code == 200

    national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
    assert national_forecast_values[0].plevels is not None
    # index 24 is the middle of the day
    assert np.abs(
        np.round(national_forecast_values[24].plevels["plevel_10"], 2)
        - np.round(national_forecast_values[24].expected_power_generation_megawatts * 0.9, 2)
        < 0.02
    )


@freeze_time("2022-01-01")
def test_read_truth_national_gsp(db_session, api_client):
    """Check main solar/GB/national/pvlive route works"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=0, label="national", status_interval_minutes=5
    ).to_orm()

    # add pv system to yield object
    gsp_yield_1_sql.location = gsp_sql_1
    gsp_yield_2_sql.location = gsp_sql_1
    gsp_yield_3_sql.location = gsp_sql_1

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_sql_1])
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/national/pvlive/")
    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 3
    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]


@freeze_time("2025-04-01 12:00")
def test_read_latest_national_values_model_name(db_session, api_client):
    """Check main national/forecast route with different model_names"""

    model = get_model(db_session, name="blend", version="0.0.1")
    model_pvnet_intraday = get_model(db_session, name="pvnet_v2", version="0.0.1")

    for m in [model, model_pvnet_intraday]:
        forecast = make_fake_national_forecast(
            session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
        )
        forecast.model = m

        db_session.add(forecast)
        update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    # default
    response = api_client.get("/v0/solar/GB/national/forecast")
    assert response.status_code == 200
    national_forecast_values_1 = [NationalForecastValue(**f) for f in response.json()]
    assert len(national_forecast_values_1) > 0
    national_forecast_values_1_sum = sum(
        [n.expected_power_generation_megawatts for n in national_forecast_values_1]
    )

    # get a model using pvnet_intraday
    response = api_client.get("/v0/solar/GB/national/forecast?model_name=pvnet_intraday")
    assert response.status_code == 200
    national_forecast_values_2 = [NationalForecastValue(**f) for f in response.json()]
    assert len(national_forecast_values_2) > 0
    national_forecast_values_2_sum = sum(
        [n.expected_power_generation_megawatts for n in national_forecast_values_2]
    )
    assert national_forecast_values_1_sum != national_forecast_values_2_sum


@freeze_time("2025-04-01 12:00")
def test_read_latest_national_values_model_name_include_metadata(db_session, api_client):
    """Check national/forecast route with different model_names and include_metadata=true"""

    model = get_model(db_session, name="blend", version="0.0.1")
    model_pvnet_intraday = get_model(db_session, name="pvnet_v2", version="0.0.1")

    for m in [model, model_pvnet_intraday]:
        forecast = make_fake_national_forecast(
            session=db_session, t0_datetime_utc=datetime.now(tz=timezone.utc)
        )
        forecast.model = m

        db_session.add(forecast)
        update_all_forecast_latest(forecasts=[forecast], session=db_session)

    app.dependency_overrides[get_session] = lambda: db_session

    # with include_metadata
    response = api_client.get("/v0/solar/GB/national/forecast?include_metadata=true")
    assert response.status_code == 200
    national_forecast_1 = NationalForecast(**response.json())
    assert len(national_forecast_1.forecast_values) > 0
    national_forecast_1_sum = sum(
        [n.expected_power_generation_megawatts for n in national_forecast_1.forecast_values]
    )

    # with include_metadata and model_name
    response = api_client.get(
        "/v0/solar/GB/national/forecast?include_metadata=true&model_name=pvnet_intraday"
    )
    assert response.status_code == 200
    national_forecast_2 = NationalForecast(**response.json())
    assert len(national_forecast_2.forecast_values) > 0
    national_forecast_2_sum = sum(
        [n.expected_power_generation_megawatts for n in national_forecast_2.forecast_values]
    )

    assert national_forecast_1_sum != national_forecast_2_sum
