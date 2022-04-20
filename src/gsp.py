"""Get GSP boundary data from eso """
import json
import logging
from typing import List, Optional

import geopandas as gpd
from fastapi import APIRouter, Depends, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import Forecast, GSPYield, ManyForecasts
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm.session import Session

from auth_utils import auth, get_user
from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_latest_national_forecast_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
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


@router.get(
    "/forecast/one_gsp/{gsp_id}",
    response_model=Forecast,
    dependencies=[Depends(auth.implicit_scheme)],
)
async def get_forecasts_for_a_specific_gsp(
    gsp_id, session: Session = Depends(get_session), user: Auth0User = Security(get_user)
) -> Forecast:
    """Get one forecast for a specific GSP id"""

    logger.info(f"Get forecasts for gsp id {gsp_id} for user {user}")

    return get_forecasts_for_a_specific_gsp_from_database(session=session, gsp_id=gsp_id)


@router.get(
    "/truth/one_gsp/{gsp_id}/",
    response_model=List[GSPYield],
    dependencies=[Depends(auth.implicit_scheme)],
)
async def get_truths_for_a_specific_gsp(
    gsp_id: int,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user),
) -> List[GSPYield]:
    """Get truth values for a specific GSP id, for yesterday and today

    Regime can "in-day" or "day-after",
    as new values are calculated around midnight when more data is available.
    If regime is not specific, the latest gsp yield is loaded.
    """

    logger.info(f"Get truth values for gsp id {gsp_id} and regime {regime} for {user}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )


@router.get("/gsp_boundaries", dependencies=[Depends(auth.implicit_scheme)])
async def get_gsp_boundaries(user: Auth0User = Security(get_user)) -> dict:
    """Get one gsp boundary for a specific GSP id

    This is a wrapper around the dataset in
    'https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points'

    The returned object is in EPSG:4326 i.e latitude and longitude
    """

    logger.info(f"Getting all GSP boundaries for {user}")

    json_string = get_gsp_boundaries_from_eso_wgs84().to_json()

    json.loads(json_string)

    return json.loads(json_string)


@router.get(
    "/forecast/all", response_model=ManyForecasts, dependencies=[Depends(auth.implicit_scheme)]
)
async def get_all_available_forecasts(
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user),
) -> ManyForecasts:
    """Get the latest information for all available forecasts"""

    logger.info(f"Get forecasts for all gsps for {user}")

    return get_forecasts_from_database(session=session)


@router.get(
    "/forecast/national", response_model=Forecast, dependencies=[Depends(auth.implicit_scheme)]
)
async def get_nationally_aggregated_forecasts(
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user),
) -> Forecast:
    """Get an aggregated forecast at the national level"""

    logger.debug(f"Get national forecasts for {user}")
    return get_latest_national_forecast_from_database(session=session)
