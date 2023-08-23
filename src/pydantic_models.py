""" pydantic models for API"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from nowcasting_datamodel.models import ForecastSQL, Location
from nowcasting_datamodel.models.utils import EnhancedBaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


class GSPYield(EnhancedBaseModel):
    """GSP Yield data"""

    datetime_utc: datetime = Field(..., description="The timestamp of the gsp yield")
    solar_generation_kw: float = Field(..., description="The amount of solar generation")


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


class OneDatetimeManyForecastValues(EnhancedBaseModel):
    datetime_utc: datetime = Field(..., description="The timestamp of the gsp yield")
    forecast_values: Dict[str, float] = Field(
        ...,
        description="List of generations by gsp_id. Key is gsp_id, value is generation_kw. "
        "We keep this as a dictionary to keep the size of the file small ",
    )


def convert_forecasts_to_many_datetime_many_generation(
    forecasts: List[ForecastSQL],
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
        gsp_id = forecast.location.gsp_id
        for forecast_value in forecast.forecast_values_latest:
            datetime_utc = forecast_value.target_time
            forecast_mw = round(forecast_value.expected_power_generation_megawatts, 2)

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
