"""Get GSP boundary data from eso """
import json
import logging
from typing import List, Optional

import geopandas as gpd
from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Location
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm.session import Session

from database import get_gsp_system, get_session

logger = logging.getLogger(__name__)


router = APIRouter()


def get_gsp_boundaries_from_eso_wgs84() -> gpd.GeoDataFrame:
    """Get GSP boundaries in lat/lon format (EPSG:4326)"""

    # get gsp boundaries
    boundaries = get_gsp_metadata_from_eso()

    # change to lat/lon - https://epsg.io/4326
    boundaries = boundaries.to_crs(4326)

    # fill nans
    boundaries = boundaries.fillna("")

    return boundaries


@router.get("/gsp_boundaries")
async def get_gsp_boundaries() -> dict:
    """Get one gsp boundary for a specific GSP id

    This is a wrapper around the dataset in
    'https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points'

    The returned object is in EPSG:4326 i.e latitude and longitude
    """

    logger.info("Getting all GSP boundaries")

    json_string = get_gsp_boundaries_from_eso_wgs84().to_json()

    json.loads(json_string)

    return json.loads(json_string)


@router.get("/gsp_systems", response_model=List[Location])
async def get_systems(
    session: Session = Depends(get_session), gsp_id: Optional[int] = None
) -> List[Location]:
    """
    Get gsp system details.

    Provide gsp_id to just return one gsp system, otherwise all are returned
    """

    logger.info(f"Get GSP systems for {gsp_id=}")

    return get_gsp_system(session=session, gsp_id=gsp_id)
