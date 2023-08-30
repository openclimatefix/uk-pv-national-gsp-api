""" pydantic models for API"""
import logging
from datetime import datetime
from typing import Dict
from typing import List, Optional

from nowcasting_datamodel.models import Location
from nowcasting_datamodel.models import LocationSQL
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


class GSPGenerations(EnhancedBaseModel):
    """gsp yields for one a singel datetime"""

    datetime_utc: datetime = Field(..., description="The timestamp of the gsp yield")
    generation_kw_by_gsp_id: Dict[str, str] = Field(
        ...,
        description="List of generations by gsp_id. Key is gsp_id, value is generation_kw. "
        "We keep this as a dictionary to keep the size of the file small ",
    )


def convert_location_sql_to_many_datetime_many_generation(
    locations: List[LocationSQL],
) -> List[GSPGenerations]:
    """Change LocationSQL to list of OneDatetimeGSPGeneration

    This converts a list of location objects to a list of OneDatetimeGSPGeneration objects.

    N locations, which T gsp yields each,
    is converted into
    T OneDatetimeGSPGeneration objects with N gsp yields each.

    This reudces the size of the object as the datetimes are not repeated for each gsp yield.
    """

    many_gsp_generation = {}

    # loop over locations and gsp yields to create a dictionary of gsp generation by datetime
    for location in locations:
        gsp_id = location.gsp_id
        for gsp_yield in location.gsp_yields:
            datetime_utc = gsp_yield.datetime_utc
            solar_generation_kw = round(gsp_yield.solar_generation_kw, 2)

            # if the datetime object is not in the dictionary, add it
            if gsp_yield.datetime_utc not in many_gsp_generation:
                many_gsp_generation[datetime_utc] = {gsp_id: solar_generation_kw}
            else:
                many_gsp_generation[datetime_utc][gsp_id] = solar_generation_kw

    # convert dictionary to list of OneDatetimeGSPGeneration objects
    many_gsp_generations = []
    for datetime_utc, gsp_generations in many_gsp_generation.items():
        many_gsp_generations.append(
            GSPGenerations(datetime_utc=datetime_utc, generation_kw_by_gsp_id=gsp_generations)
        )

    return many_gsp_generations
