"""Get GSP boundary data from eso """
import json
import logging
from typing import List, Optional

import geopandas as gpd
from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast, ForecastValue, GSPYield, Location, ManyForecasts
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm.session import Session

from database import (
    get_gsp_system,
    get_session,
)

logger = logging.getLogger(__name__)


router = APIRouter()
NationalYield = GSPYield

# corresponds to /v0/system/GB/gsp/boundaries
def get_gsp_boundaries_from_eso_wgs84() -> gpd.GeoDataFrame:
    """Get GSP boundaries in lat/lon format (EPSG:4326)"""

    # get gsp boundaries
    boundaries = get_gsp_metadata_from_eso()

    # change to lat/lon - https://epsg.io/4326
    boundaries = boundaries.to_crs(4326)

    # fill nans
    boundaries = boundaries.fillna("")

    return boundaries

# corresponds to API route /v0/system/GB/gsp/boundaries
@router.get("/boundaries")
async def get_gsp_boundaries() -> dict:
    """### Get one GSP boundary for a specific GSP

    This route is still under construction...

    [This is a wrapper around the dataset]
    (https://data.nationalgrideso.com/systemgis-boundaries-for-gb-grid-supply-points).

    Returns an object that is in EPSG:4326 (ie. latitude & longitude coordinates).

    """

    logger.info("Getting all GSP boundaries")

    json_string = get_gsp_boundaries_from_eso_wgs84().to_json()

    json.loads(json_string)

    return json.loads(json_string)


# corresponds to API route /v0/system/GB/gsp/, get system details for all GSPs
@router.get("/", response_model=List[Location])
async def get_systems(
    session: Session = Depends(get_session), gsp_id: Optional[int] = None
) -> List[Location]:
    """### Get system details for a single GSP or all GSPs

    Returns an object with the system details of a given GSP using the
    gsp_id parameter.

    Provide one gsp_id to return system details for that GSP, otherwise details for ALL
    grid systems will be returned.

    Please see __Location__ schema for metadata details.

    #### Parameters
    - gsp_id: gsp_id of the requested system
    - NB: If no parameter is entered, system details for all 300+ GSPs are returned.

    """

    logger.info(f"Get GSP systems for {gsp_id=}")

    return get_gsp_system(session=session, gsp_id=gsp_id)
