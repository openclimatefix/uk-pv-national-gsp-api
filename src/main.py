""" Main FastAPI app """
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID, uuid4

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field, validator

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

version = "0.1.2"
description = """
The Nowcasting API is still under development. It only returns fake results.
"""
app = FastAPI(
    title="Nowcasting API",
    version=version,
    description=description,
    contact={
        "name": "Open Climate Fix",
        "url": "https://openclimatefix.org",
        "email": "info@openclimatefix.org",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/openclimatefix/nowcasting_api/blob/main/LICENSE",
    },
)

thirty_minutes = timedelta(minutes=30)


def datetime_must_have_timezone(cls, v: datetime):
    """Enforce that this variable must have a timezone"""
    if v.tzinfo is None:
        raise ValueError(f"{v} must have a timezone")
    return v


def convert_to_camelcase(snake_str: str) -> str:
    """Converts a given snake_case string into camelCase"""
    first, *others = snake_str.split("_")
    return "".join([first.lower(), *map(str.title, others)])


class EnhancedBaseModel(BaseModel):
    """Ensures that attribute names are returned in camelCase"""

    # Automatically creates camelcase alias for field names
    # See https://pydantic-docs.helpmanual.io/usage/model_config/#alias-generator
    class Config:  # noqa: D106
        alias_generator = convert_to_camelcase
        allow_population_by_field_name = True


class ForecastValue(EnhancedBaseModel):
    """One Forecast of generation at one timestamp"""

    target_time: datetime = Field(
        ...,
        description="The target time that the forecast is produced for",
    )
    expected_pv_power_generation_megawatts: float = Field(
        ..., ge=0, description="The forecasted value in MW"
    )

    _normalize_target_time = validator("target_time", allow_reuse=True)(datetime_must_have_timezone)


class AdditionalLocationInformation(EnhancedBaseModel):
    """Used internally to better describe a Location"""

    gsp_id: Optional[int] = Field(None, description="The Grid Supply Point (GSP) id")
    gsp_name: Optional[str] = Field(None, description="The GSP name")
    gsp_group: Optional[str] = Field(None, description="The GSP group name")
    region_name: Optional[str] = Field(..., description="The GSP region name")


class Location(EnhancedBaseModel):
    """Location that the forecast is for"""

    location_id: UUID = Field(..., description="OCF-created id for location")
    label: str = Field(..., description="User-defined name for the location")
    additional_information: AdditionalLocationInformation = Field(
        ..., description="E.g. Existing GSP properties"
    )


class InputDataLastUpdated(EnhancedBaseModel):
    """Information about the input data that was used to create the forecast"""

    gsp: datetime = Field(..., description="The time when the input GSP data was last updated")
    nwp: datetime = Field(..., description="The time when the input NWP data was last updated")
    pv: datetime = Field(..., description="The time when the input PV data was last updated")
    satellite: datetime = Field(
        ..., description="The time when the input satellite data was last updated"
    )

    _normalize_gsp = validator("gsp", allow_reuse=True)(datetime_must_have_timezone)
    _normalize_nwp = validator("nwp", allow_reuse=True)(datetime_must_have_timezone)
    _normalize_pv = validator("pv", allow_reuse=True)(datetime_must_have_timezone)
    _normalize_satellite = validator("satellite", allow_reuse=True)(datetime_must_have_timezone)


class Forecast(EnhancedBaseModel):
    """A single Forecast"""

    location: Location = Field(..., description="The location object for this forecaster")
    forecast_creation_time: datetime = Field(
        ..., description="The time when the forecaster was made"
    )
    forecast_values: List[ForecastValue] = Field(
        ...,
        description="List of forecasted value objects. Each value has the datestamp and a value",
    )
    input_data_last_updated: InputDataLastUpdated = Field(
        ...,
        description="Information about the input data that was used to create the forecast",
    )

    _normalize_forecast_creation_time = validator("forecast_creation_time", allow_reuse=True)(
        datetime_must_have_timezone
    )


class ManyForecasts(EnhancedBaseModel):
    """Many Forecasts"""

    forecasts: List[Forecast] = Field(
        ...,
        description="List of forecasts for different GSPs",
    )


def _create_dummy_forecast_for_location(location: Location):
    logger.debug(f'Creating dummy forecast for location {location}')

    # get datetime right now
    now = datetime.now(timezone.utc)
    now_floor_30 = _floor_30_minutes_dt(dt=now)

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


def _create_dummy_national_forecast():
    """Create a dummy forecast for the national level"""

    logger.debug('Creating dummy forecast')

    additional_information = AdditionalLocationInformation(
        region_name="national_GB",
    )

    location = Location(
        location_id=uuid4(),
        label="GB (National)",
        additional_information=additional_information,
    )

    return _create_dummy_forecast_for_location(location=location)


def _create_dummy_gsp_forecast(gsp_id):
    """Create a dummy forecast for a given GSP"""

    logger.debug(f'Creating dummy forecast for {gsp_id=}')

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

    return _create_dummy_forecast_for_location(location=location)


@app.get("/")
def get_api_information():
    """Get information about the API itself"""

    logger.info('Route / has be called')

    return {
        "title": "Nowcasting API",
        "version": version,
        "description": description,
        "documentation": "https://api.nowcasting.io/docs",
    }


@app.get("/v0/forecasts/GB/pv/gsp/{gsp_id}", response_model=Forecast)
def get_forecasts_for_a_specific_gsp(gsp_id) -> Forecast:
    """Get one forecast for a specific GSP id"""

    logger.info(f'Get forecasts for gsp id {gsp_id}')

    return _create_dummy_gsp_forecast(gsp_id=gsp_id)


@app.get("/v0/forecasts/GB/pv/gsp", response_model=ManyForecasts)
def get_all_available_forecasts() -> ManyForecasts:
    """Get the latest information for all available forecasts"""

    logger.info('Get forecasts for all gsps')

    return ManyForecasts(forecasts=[_create_dummy_gsp_forecast(gsp_id) for gsp_id in range(10)])


@app.get("/v0/forecasts/GB/pv/national", response_model=Forecast)
def get_nationally_aggregated_forecasts() -> Forecast:
    """Get an aggregated forecast at the national level"""

    logger.debug('Get national forecasts')

    return _create_dummy_national_forecast()


def _floor_30_minutes_dt(dt):
    """
    Floor a datetime by 30 mins.

    For example:
    2021-01-01 17:01:01 --> 2021-01-01 17:00:00
    2021-01-01 17:35:01 --> 2021-01-01 17:30:00

    :param dt:
    :return:
    """
    approx = np.floor(dt.minute / 30.0) * 30
    dt = dt.replace(minute=0)
    dt = dt.replace(second=0)
    dt = dt.replace(microsecond=0)
    dt += timedelta(minutes=approx)

    return dt
