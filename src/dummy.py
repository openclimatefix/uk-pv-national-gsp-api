from datetime import datetime, timezone, timedelta
from uuid import uuid4

from main import logger, thirty_minutes
from models import ForecastValue, AdditionalLocationInformation, Location, InputDataLastUpdated, Forecast
from utils import floor_30_minutes_dt


def create_dummy_forecast_for_location(location: Location):
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
        ForecastValue(expected_pv_power_generation_megawatts=0, target_time=datetime_utc)
        for datetime_utc in datetimes_utc
    ]

    forecast_creation_time = now_floor_30 - timedelta(minutes=30)
    return Forecast(
        location=location,
        forecast_creation_time=forecast_creation_time,
        forecast_values=forecast_values,
        input_data_last_updated=input_data_last_updated,
    )


def create_dummy_national_forecast():
    """Create a dummy forecast for the national level"""

    logger.debug("Creating dummy forecast")

    additional_information = AdditionalLocationInformation(
        region_name="national_GB",
    )

    location = Location(
        location_id=uuid4(),
        label="GB (National)",
        additional_information=additional_information,
    )

    return create_dummy_forecast_for_location(location=location)


def create_dummy_gsp_forecast(gsp_id):
    """Create a dummy forecast for a given GSP"""

    logger.debug(f"Creating dummy forecast for {gsp_id=}")

    additional_information = AdditionalLocationInformation(
        gsp_id=gsp_id,
        gsp_name="dummy_gsp_name",
        gsp_group="dummy_gsp_group",
        region_name="dummy_region_name",
    )

    location = Location(
        location_id=uuid4(),
        label="dummy_label",
        additional_information=additional_information,
    )

    return create_dummy_forecast_for_location(location=location)