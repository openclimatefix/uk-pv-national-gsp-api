""" pydantic models for API"""
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from nowcasting_datamodel.models import Forecast, ForecastSQL, ForecastValue, Location, LocationSQL
from nowcasting_datamodel.models.utils import EnhancedBaseModel
from pydantic import Field, validator

logger = logging.getLogger(__name__)


adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))


class GSPYield(EnhancedBaseModel):
    """GSP Yield data"""

    datetime_utc: datetime = Field(..., description="The timestamp of the gsp yield")
    solar_generation_kw: float = Field(..., description="The amount of solar generation")

    @validator("solar_generation_kw")
    def result_check(cls, v):
        """Round to 2 decimal places"""
        return round(v, 2)


class LocationWithGSPYields(Location):
    """Location object with GSPYields"""

    gsp_yields: Optional[List[GSPYield]] = Field([], description="List of gsp yields")

    def from_location_sql(self):
        """Change LocationWithGSPYieldsSQL to LocationWithGSPYields

        LocationWithGSPYieldsSQL is defined in nowcasting_datamodel
        """

        return LocationWithGSPYields(
            label=self.label,
            gsp_id=self.gsp_id,
            gsp_name=self.gsp_name,
            gsp_group=self.gsp_group,
            region_name=self.region_name,
            installed_capacity_mw=self.installed_capacity_mw,
            gsp_yields=[
                GSPYield(
                    datetime_utc=gsp_yield.datetime_utc,
                    solar_generation_kw=gsp_yield.solar_generation_kw,
                )
                for gsp_yield in self.gsp_yields
            ],
        )


class GSPYieldGroupByDatetime(EnhancedBaseModel):
    """gsp yields for one a singel datetime"""

    datetime_utc: datetime = Field(..., description="The timestamp of the gsp yield")
    generation_kw_by_gsp_id: Dict[int, float] = Field(
        ...,
        description="List of generations by gsp_id. Key is gsp_id, value is generation_kw. "
        "We keep this as a dictionary to keep the size of the file small ",
    )


class OneDatetimeManyForecastValues(EnhancedBaseModel):
    """One datetime with many forecast values"""

    datetime_utc: datetime = Field(..., description="The timestamp of the gsp yield")
    forecast_values: Dict[int, float] = Field(
        ...,
        description="List of forecasts by gsp_id. Key is gsp_id, value is generation_kw. "
        "We keep this as a dictionary to keep the size of the file small ",
    )


def convert_location_sql_to_many_datetime_many_generation(
    locations: List[LocationSQL],
) -> List[GSPYieldGroupByDatetime]:
    """Change LocationSQL to list of OneDatetimeGSPGeneration

    This converts a list of location objects to a list of OneDatetimeGSPGeneration objects.

    N locations, which T gsp yields each,
    is converted into
    T OneDatetimeGSPGeneration objects with N gsp yields each.

    This reducs the size of the object as the datetimes are not repeated for each gsp yield.
    """

    many_gsp_generation = {}

    # loop over locations and gsp yields to create a dictionary of gsp generation by datetime
    for location in locations:
        gsp_id = str(location.gsp_id)
        for gsp_yield in location.gsp_yields:
            datetime_utc = gsp_yield.datetime_utc
            solar_generation_kw = str(round(gsp_yield.solar_generation_kw, 2))

            # if the datetime object is not in the dictionary, add it
            if gsp_yield.datetime_utc not in many_gsp_generation:
                many_gsp_generation[datetime_utc] = {gsp_id: solar_generation_kw}
            else:
                many_gsp_generation[datetime_utc][gsp_id] = solar_generation_kw

    # convert dictionary to list of OneDatetimeGSPGeneration objects
    many_gsp_generations = []
    for datetime_utc, gsp_generations in many_gsp_generation.items():
        many_gsp_generations.append(
            GSPYieldGroupByDatetime(
                datetime_utc=datetime_utc, generation_kw_by_gsp_id=gsp_generations
            )
        )

    return many_gsp_generations


def convert_forecasts_to_many_datetime_many_generation(
    forecasts: List[ForecastSQL],
    historic: bool = True,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
) -> List[OneDatetimeManyForecastValues]:
    """Change forecasts to list of OneDatetimeManyForecastValues

    This converts a list of forecast objects to a list of OneDatetimeManyForecastValues objects.

    N forecasts, which T forecast values each,
    is converted into
    T OneDatetimeManyForecastValues objects with N forecast values each.

    This reduces the size of the object as the datetimes are not repeated for each forecast values.
    """

    many_forecast_values_by_datetime = {}

    # loop over locations and gsp yields to create a dictionary of gsp generation by datetime
    for forecast in forecasts:
        gsp_id = str(forecast.location.gsp_id)
        if historic:
            forecast_values = forecast.forecast_values_latest
        else:
            forecast_values = forecast.forecast_values

        for forecast_value in forecast_values:
            datetime_utc = forecast_value.target_time
            if start_datetime_utc is not None and datetime_utc < start_datetime_utc:
                continue
            if end_datetime_utc is not None and datetime_utc > end_datetime_utc:
                continue

            forecast_mw = forecast_value.expected_power_generation_megawatts

            # adjust the value if gsp id 0, this is the national
            if gsp_id == "0":
                adjust_mw = forecast_value.adjust_mw
                if adjust_mw > adjust_limit:
                    adjust_mw = adjust_limit
                elif adjust_mw < -adjust_limit:
                    adjust_mw = -adjust_limit

                forecast_mw = forecast_mw - adjust_mw

                if forecast_mw < 0:
                    forecast_mw = 0.0

            forecast_mw = round(forecast_mw, 2)

            # if the datetime object is not in the dictionary, add it
            if datetime_utc not in many_forecast_values_by_datetime:
                many_forecast_values_by_datetime[datetime_utc] = {gsp_id: forecast_mw}
            else:
                many_forecast_values_by_datetime[datetime_utc][gsp_id] = forecast_mw

    # convert dictionary to list of OneDatetimeManyForecastValues objects
    many_forecast_values = []
    for datetime_utc, forecast_values in many_forecast_values_by_datetime.items():
        many_forecast_values.append(
            OneDatetimeManyForecastValues(
                datetime_utc=datetime_utc, forecast_values=forecast_values
            )
        )

    return many_forecast_values


NationalYield = GSPYield


class NationalForecastValue(ForecastValue):
    """One Forecast of generation at one timestamp include properties"""

    class Config:
        fields = {
            "expected_power_generation_normalized": {"exclude": True},
        }

    plevels: dict = Field(
        None, description="Dictionary to hold properties of the forecast, like p_levels. "
    )

    @validator("expected_power_generation_megawatts")
    def result_check(cls, v):
        """Round to 2 decimal places"""
        return round(v, 2)


class NationalForecast(Forecast):
    """One Forecast of generation at one timestamp"""

    forecast_values: List[NationalForecastValue] = Field(..., description="List of forecast values")
