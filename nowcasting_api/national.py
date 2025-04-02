from enum import Enum

"""National API routes"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Union

import pandas as pd
import structlog
from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
)
from elexonpy.api.generation_forecast_api import GenerationForecastApi
from elexonpy.api_client import ApiClient
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.read.read import get_latest_forecast_for_gsps
from pydantic_models import (
    NationalForecast,
    NationalForecastValue,
    NationalYield,
    SolarForecastResponse,
    SolarForecastValue,
)
from sqlalchemy.orm.session import Session
from utils import N_CALLS_PER_HOUR, filter_forecast_values, format_datetime, format_plevels, limiter

logger = structlog.stdlib.get_logger()

adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))
get_plevels = bool(os.getenv("GET_PLEVELS", True))


class ModelName(str, Enum):
    blend = "blend"
    pvnet_v2 = "pvnet_v2"
    pvnet_da = "pvnet_da"
    pvnet_ecwmf = "pvnet_ecwmf"


router = APIRouter(
    tags=["National"],
)

# Initialize Elexon API client
api_client = ApiClient()
elexon_forecast_api = GenerationForecastApi(api_client)


@router.get(
    "/forecast",
    response_model=Union[NationalForecast, List[NationalForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_national_forecast(
    request: Request,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
    include_metadata: bool = False,
    start_datetime_utc: Optional[str] = None,
    end_datetime_utc: Optional[str] = None,
    creation_limit_utc: Optional[str] = None,
    model_name: ModelName = ModelName.blend,  # Added model name parameter
) -> Union[NationalForecast, List[NationalForecastValue]]:
    """
    Fetch national forecasts with an optional model selection.
    """
    logger.debug(f"Get national forecasts using model {model_name}")

    start_datetime_utc = format_datetime(start_datetime_utc)
    end_datetime_utc = format_datetime(end_datetime_utc)
    creation_limit_utc = format_datetime(creation_limit_utc)

    logger.debug("Getting forecast.")
    if include_metadata:
        if forecast_horizon_minutes is not None:
            raise HTTPException(
                status_code=404,
                detail="Can not set forecast_horizon_minutes when including metadata",
            )

        historic = creation_limit_utc is None

        forecast = get_latest_forecast_for_gsps(
            session=session,
            gsp_ids=[0],
            model_name=model_name.value,  # Pass the selected model name
            historic=historic,
            preload_children=True,
            start_target_time=start_datetime_utc,
            end_target_time=end_datetime_utc,
            end_created_utc=creation_limit_utc,
        )
        forecast = forecast[0]

        forecast = (
            NationalForecast.from_orm_latest(forecast)
            if historic
            else NationalForecast.from_orm(forecast)
        )

        forecasts = filter_forecast_values(
            forecasts=[forecast],
            start_datetime_utc=start_datetime_utc,
            end_datetime_utc=end_datetime_utc,
        )
        forecast_values = forecasts[0].forecast_values

    else:
        forecast_values = get_latest_forecast_values_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=0,
            forecast_horizon_minutes=forecast_horizon_minutes,
            start_datetime_utc=start_datetime_utc,
            end_datetime_utc=end_datetime_utc,
            creation_utc_limit=creation_limit_utc,
        )

    logger.debug(f"Got national forecasts with {len(forecast_values)} forecast values.")
    forecast_values = [f.adjust(limit=adjust_limit) for f in forecast_values]

    if include_metadata:
        forecast.forecast_values = forecast_values
        return forecast
    else:
        return forecast_values
