"""Get GSP boundary data from eso """
import logging

import geopandas as gpd
from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm.session import Session

from database import get_forecasts_for_a_specific_gsp_from_database, get_session

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


@router.get("/gsp/{gsp_id}", response_model=Forecast)
async def get_forecasts_for_a_specific_gsp(
    gsp_id, session: Session = Depends(get_session)
) -> Forecast:
    """Get one forecast for a specific GSP id"""

    logger.info(f"Get forecasts for gsp id {gsp_id}")

    return get_forecasts_for_a_specific_gsp_from_database(session=session, gsp_id=gsp_id)


@router.get("/gsp_boundaries")
async def get_gsp_boundaries() -> dict:
    """Get one gsp boundary for a specific GSP id

    This is a wrapper around the dataset in
    'https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points'

    The returned object is in EPSG:4326 i.e latitude and longitude
    """

    logger.info("Getting all GSP boundaries")

    return get_gsp_boundaries_from_eso_wgs84().to_dict()
