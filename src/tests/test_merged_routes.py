""" Test for main app """
from datetime import datetime, timezone

from freezegun import freeze_time
from nowcasting_datamodel.fake import make_fake_forecast, make_fake_forecasts
from nowcasting_datamodel.models import Forecast, ForecastValue, ForecastValueLatestSQL
from nowcasting_datamodel.save.update import update_all_forecast_latest

from database import get_session
from main import app



@freeze_time("2022-06-01")
def test_read_forecast_values_gsp(db_session, api_client):
    """Check main solar/GB/gsp/{gsp_id}/forecast route works"""

    forecast_value_1_sql = ForecastValueLatestSQL(
        target_time=datetime(2023, 6, 2), expected_power_generation_megawatts=1, gsp_id=1
    )

    forecast_value_2_sql = ForecastValueLatestSQL(
        target_time=datetime(2023, 6, 1, 1), expected_power_generation_megawatts=2, gsp_id=1
    )

    forecast_value_3_sql = ForecastValueLatestSQL(
        target_time=datetime(2023, 6, 1), expected_power_generation_megawatts=3, gsp_id=1
    )

    forecast = make_fake_forecast(
        gsp_id=1, session=db_session, t0_datetime_utc=datetime(2023, 1, 1)
    )
    forecast.forecast_values_latest.append(forecast_value_1_sql)
    forecast.forecast_values_latest.append(forecast_value_2_sql)
    forecast.forecast_values_latest.append(forecast_value_3_sql)

    # add to database
    db_session.add_all([forecast])

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/solar/GB/gsp/1/forecast")
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
