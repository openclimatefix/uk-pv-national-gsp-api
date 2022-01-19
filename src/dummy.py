""" Create dummy forecasts for testing """
import logging
from datetime import datetime, timedelta, timezone

from nowcasting_forecast.database.models import (
    Forecast,
    ForecastValue,
    InputDataLastUpdated,
    Location,
)

from utils import floor_30_minutes_dt

logger = logging.getLogger(__name__)

thirty_minutes = timedelta(minutes=30)


def create_dummy_forecast_for_location(location: Location) -> Forecast:
    """Create dummy forecast for one location"""
    logger.debug(f"Creating dummy forecast for location {location}")

    # get datetime right now
    now = datetime.now(timezone.utc)
    now_floor_30 = floor_30_minutes_dt(dt=now)

    # make list of datetimes that the forecast is for
    datetimes_utc = [now_floor_30 + i * thirty_minutes for i in range(4)]

    input_data_last_updated = InputDataLastUpdated(
        gsp=now_floor_30,
        nwp=now_floor_30,
        pv=now_floor_30,
        satellite=now_floor_30,
    )

    forecast_values = [
        ForecastValue(expected_power_generation_megawatts=0, target_time=datetime_utc)
        for datetime_utc in datetimes_utc
    ]

    forecast_creation_time = now_floor_30 - timedelta(minutes=30)
    return Forecast(
        location=location,
        forecast_creation_time=forecast_creation_time,
        forecast_values=forecast_values,
        input_data_last_updated=input_data_last_updated,
    )


def create_dummy_national_forecast() -> Forecast:
    """Create a dummy forecast for the national level"""

    logger.debug("Creating dummy forecast")

    location = Location(
        label="GB (National)",
        region_name="national_GB",
        gsp_name="dummy_gsp_name",
        gsp_group="dummy_gsp_group",
    )

    return create_dummy_forecast_for_location(location=location)

