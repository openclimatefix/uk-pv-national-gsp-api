"""Get GSP boundary data from eso """
import json
from typing import List, Optional

import geopandas as gpd
import structlog
from fastapi import APIRouter, Depends, Request, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import GSPYield, Location
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import get_gsp_system, get_session
from utils import N_CALLS_PER_HOUR, limiter

# flake8: noqa: E501
logger = structlog.stdlib.get_logger()


router = APIRouter()
NationalYield = GSPYield

# corresponds to API route /v0/system/GB/gsp/, get system details for all GSPs
@router.get(
    "/",
    response_model=List[Location],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_system_details(
    request: Request,
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
