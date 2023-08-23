""" pydantic models for API"""
import logging
from datetime import datetime
from typing import List, Optional

from nowcasting_datamodel.models import Location
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
        """ Change LocationWithGSPYieldsSQL to LocationWithGSPYields

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
