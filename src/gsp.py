"""Get GSP boundary data from eso """
import logging

import geopandas as gpd
from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast, ManyForecasts
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm import Session
from sqlalchemy.orm.session import Session

from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_session,
    get_forecasts_from_database,
    get_latest_national_forecast_from_database,
)


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


@router.get("/forecast/one_gsp/{gsp_id}", response_model=Forecast)
async def get_forecasts_for_a_specific_gsp(
    gsp_id, session: Session = Depends(get_session)
) -> Forecast:
    """Get one forecast for a specific GSP id

    If 'gsp_id' is None, all forecast for all GSPs are returned
    """

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


@router.get("/forecast/all", response_model=ManyForecasts)
async def get_all_available_forecasts(session: Session = Depends(get_session)) -> ManyForecasts:
    """Get the latest information for all available forecasts"""

    logger.info("Get forecasts for all gsps")

    return get_forecasts_from_database(session=session)


@router.get("/forecast/national", response_model=Forecast)
async def get_nationally_aggregated_forecasts(session: Session = Depends(get_session)) -> Forecast:
    """Get an aggregated forecast at the national level"""

    logger.debug("Get national forecasts")
    return get_latest_national_forecast_from_database(session=session)
