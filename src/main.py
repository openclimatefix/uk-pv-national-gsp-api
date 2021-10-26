""" Main FastAPI app """
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID, uuid4

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field, validator

version = "0.1.0"

app = FastAPI(title="Nowcasting API", version=version, contact={"name": "Open Climate Fix"})

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

    class Config:  # noqa: D106
        alias_generator = convert_to_camelcase
        allow_population_by_field_name = True


class ForecastedValue(EnhancedBaseModel):
    """One Forecast of generation at one timestamp"""

    effective_time: datetime = Field(..., description="The time for the forecasted value")
    pv_power_generation_megawatts: float = Field(
        ..., ge=0, description="The forecasted value in MW"
    )

    _normalize_effective_time = validator("effective_time", allow_reuse=True)(
        datetime_must_have_timezone
    )


class AdditionalLocationInformation(EnhancedBaseModel):
    """Used internally to better describe a Location"""

    gsp_id: int = Field(..., description="The Grid Supply Point (GSP) id")
    gsp_name: str = Field(..., description="The GSP name")
    gsp_group: str = Field(..., description="The GSP group name")
    region_name: str = Field(..., description="The GSP region name")


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
    forecasted_values: List[ForecastedValue] = Field(
        ...,
        description="List of forecasted value objects. Each value has the datestamp and a value",
    )
    input_data_last_updated: InputDataLastUpdated = Field(
        ..., description="Information about the input data that was used to create the forecast"
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


def create_dummy_forecast(gsp_id):
    """Create a dummy forecast for a given gsp"""
    # get datetime right now
    now = datetime.now(timezone.utc)
    now_floor_30 = _floor_30_minutes_dt(dt=now)

    # make list of datetimes that the forecast is for
    datetimes_utc = [now_floor_30 + i * thirty_minutes for i in range(4)]

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

    input_data_last_updated = InputDataLastUpdated(
        gsp=now_floor_30,
        nwp=now_floor_30,
        pv=now_floor_30,
        satellite=now_floor_30,
    )

    forecasted_values = [
        ForecastedValue(pv_power_generation_megawatts=0, effective_time=datetime_utc)
        for datetime_utc in datetimes_utc
    ]

    forecast_creation_time = now_floor_30 - timedelta(minutes=30)
    return Forecast(
        location=location,
        forecast_creation_time=forecast_creation_time,
        forecasted_values=forecasted_values,
        input_data_last_updated=input_data_last_updated,
    )


@app.get("/")
def read_root():
    """Default root"""
    return {
        "title": "Nowcasting API",
        "version": version,
        "documentation": " go to /docs/ to see documentation",
    }


@app.get("/v0/forecasts/gsp/{gsp_id}", response_model=Forecast)
def get_forecast_gsp(gsp_id) -> Forecast:
    """
    Get one forecast for a specific GSP id
    """
    # just make dummy data for the moment
    return create_dummy_forecast(gsp_id=gsp_id)


@app.get("/v0/forecasts/gsp", response_model=ManyForecasts)
def get_forecasts() -> ManyForecasts:
    """Get the latest information for all available forecasts"""
    return ManyForecasts(forecasts=[create_dummy_forecast(gsp_id) for gsp_id in range(10)])


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
