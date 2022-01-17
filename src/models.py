from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, validator

from utils import convert_to_camelcase, datetime_must_have_timezone


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