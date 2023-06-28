"""Get GSP boundary data from eso """
import json
from typing import List, Optional

import geopandas as gpd
import structlog
from fastapi import APIRouter, Depends, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import GSPYield, Location
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import get_gsp_system, get_session

# flake8: noqa: E501
logger = structlog.stdlib.get_logger()


router = APIRouter()
NationalYield = GSPYield


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
@router.get(
    "/boundaries",
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_gsp_boundaries(
    user: Auth0User = Security(get_user()),
) -> dict:
    """### Get GSP boundaries

    Returns an object with GSP boundaries provided by National Grid ESO.

    [This is a wrapper around the dataset](https://data.nationalgrideso.com/systemgis-boundaries-for-gb-grid-supply-points).

    The return object is in EPSG:4326 (ie. contains latitude & longitude
    coordinates).

    """

    logger.info(f"Getting all GSP boundaries for user {user}")

    json_string = get_gsp_boundaries_from_eso_wgs84().to_json()

    json.loads(json_string)

    return json.loads(json_string)


# corresponds to API route /v0/system/GB/gsp/, get system details for all GSPs
@router.get(
    "/",
    response_model=List[Location],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_system_details(
    session: Session = Depends(get_session),
    gsp_id: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> List[Location]:
    """### Get system details for a single GSP or all GSPs

    Returns an object with system details of a given GSP using the
    _gsp_id_ query parameter, otherwise details for all supply points are provided.

    #### Parameters
    - **gsp_id**: gsp_id of the requested system
    """

    logger.info(f"Get GSP systems for {gsp_id=} for {user}")

    return get_gsp_system(session=session, gsp_id=gsp_id)
