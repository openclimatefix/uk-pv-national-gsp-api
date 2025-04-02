"""National API routes.

This module defines the API routes for national solar forecasts, including endpoints
for fetching forecast data from various models and real-time PV_Live readings.
"""

import os
from typing import List, Optional, Union

import structlog
from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
)
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.read.read import get_latest_forecast_for_gsps
from pydantic import BaseModel
from sqlalchemy.orm.session import Session
from utils import N_CALLS_PER_HOUR, filter_forecast_values, limiter
from enum import Enum

logger = structlog.stdlib.get_logger()

adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))
get_plevels = bool(os.getenv("GET_PLEVELS", True))

router = APIRouter(
    tags=["National"],
)

class ModelName(str, Enum):
    """Enumeration of available forecast models."""
    blend = "blend"
    pvnet_v2 = "pvnet_v2"
    pvnet_da = "pvnet_da"
    pvnet_ecwmf = "pvnet_ecwmf"

@router.get(
    "/forecast",
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_national_forecast(
    session: Session = Depends(get_session),
    model_name: ModelName = ModelName.blend,
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
    include_metadata: bool = False,
    start_datetime_utc: Optional[str] = None,
    end_datetime_utc: Optional[str] = None,
    creation_limit_utc: Optional[str] = None,
):
    """Fetch national forecasts based on the selected model name."""
    logger.debug("Get national forecasts with model: %s", model_name)

    forecast = get_latest_forecast_for_gsps(
        session=session,
        gsp_ids=[0],
        model_name=model_name.value,
        historic=creation_limit_utc is None,
        preload_children=True,
        start_target_time=start_datetime_utc,
        end_target_time=end_datetime_utc,
        end_created_utc=creation_limit_utc,
    )

    if not forecast:
        raise HTTPException(status_code=404, detail="No forecasts available.")

    return forecast