"""Fetch BMRS forecast data."""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Union

import pandas as pd
from sqlalchemy.orm.session import Session

import structlog
from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_latest_forecast_values_for_a_specific_gsp_from_database, get_session,
    get_truth_values_for_a_specific_gsp_from_database)
from elexonpy.api.generation_forecast_api import GenerationForecastApi
from elexonpy.api_client import ApiClient
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.read.read import get_latest_forecast_for_gsps
from pydantic_models import (NationalForecast, NationalForecastValue,
                             NationalYield)
from utils import (N_CALLS_PER_HOUR, filter_forecast_values, format_datetime,
                   format_plevels, limiter)

logger = structlog.stdlib.get_logger()

adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))
get_plevels = bool(os.getenv("GET_PLEVELS", True))

router = APIRouter(
    tags=["National"],
)

# Initialize Elexon API client
api_client = ApiClient()
forecast_api = GenerationForecastApi(api_client)


@router.get("/bmrs", summary="Get BMRS Forecast")

@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_bmrs_forecast(
    request: Request,
    start_datetime_utc: datetime = Query(
        default=datetime.utcnow() - timedelta(days=3), description="Start date and time in UTC"
    ),
    end_datetime_utc: datetime = Query(
        default=datetime.utcnow() + timedelta(days=3), description="End date and time in UTC"
    ),
    process_type: str = Query("Day Ahead", description="Process type"),
):
    """
    Fetch BMRS solar forecasts from the Elexon API.

    Parameters:
    - start_datetime_utc (datetime): Start date and time in UTC.
    - end_datetime_utc (datetime): End date and time in UTC.
    - process_type (str): Process type for the forecast.

    Returns:
    - dict: Dictionary containing the fetched BMRS forecast data.

    """
    # Fetch data using the forecast API
    response = forecast_api.forecast_generation_wind_and_solar_day_ahead_get(
        _from=start_datetime_utc, to=end_datetime_utc, process_type=process_type, format="json"
    )

    # Convert response to DataFrame
    df = pd.DataFrame([item.to_dict() for item in response.data])

    # Return as JSON
    return {"data": df.to_dict(orient="records")}


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
) -> Union[NationalForecast, List[NationalForecastValue]]:
    """

    Fetch national forecasts.

    This route returns the most recent forecast for each _target_time_.

    The _forecast_horizon_minutes_ parameter allows
    a user to query for a forecast that is made this number, or horizon, of
    minutes before the _target_time_.

    For example, if the target time is 10am today, the forecast made at 2am
    today is the 8-hour forecast for 10am, and the forecast made at 6am for
    10am today is the 4-hour forecast for 10am.

    #### Parameters
    - **forecast_horizon_minutes**: optional forecast horizon in minutes (ex.
    60 returns the forecast made an hour before the target time)
    - **start_datetime_utc**: optional start datetime for the query.
    - **end_datetime_utc**: optional end datetime for the query.
    - **creation_utc_limit**: optional, only return forecasts made before this datetime.
    Note you can only go 7 days back at the moment

    Returns:
        dict: The national forecast data.

    """
    logger.debug("Get national forecasts")

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

        if creation_limit_utc is None:
            historic = True
        else:
            historic = False

        forecast = get_latest_forecast_for_gsps(
            session=session,
            gsp_ids=[0],
            model_name="blend",
            historic=historic,
            preload_children=True,
            start_target_time=start_datetime_utc,
            end_target_time=end_datetime_utc,
            end_created_utc=creation_limit_utc,
        )
        forecast = forecast[0]

        if historic:
            forecast = NationalForecast.from_orm_latest(forecast)
        else:
            forecast = NationalForecast.from_orm(forecast)

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

    logger.debug(
        f"Got national forecasts with {len(forecast_values)} forecast values. "
        f"Now adjusting by at most {adjust_limit} MW"
    )

    forecast_values = [f.adjust(limit=adjust_limit) for f in forecast_values]

    if not get_plevels:
        logger.debug("Not getting plevels")
        national_forecast_values = [NationalForecastValue(**f.__dict__) for f in forecast_values]
    else:
        logger.debug("Getting plevels")
        # change to NationalForecastValue
        national_forecast_values = []
        for f in forecast_values:
            # change to NationalForecastValue
            plevels = f._properties
            national_forecast_value = NationalForecastValue(**f.__dict__)
            national_forecast_value.plevels = plevels

            # add default values in, we will remove this at some point
            format_plevels(national_forecast_value)

            national_forecast_values.append(national_forecast_value)
    if include_metadata:
        # return full forecast object
        forecast.forecast_values = national_forecast_values
        return forecast
    else:
        return national_forecast_values


# corresponds to API route /v0/solar/GB/national/pvlive/, getting PV_Live NationalYield for GB
@router.get(
    "/pvlive",
    response_model=List[NationalYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_national_pvlive(
    request: Request,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[NationalYield]:
    """### Get national PV_Live values.

    Returns a series of real-time solar energy generation readings from
    PV_Live for all of Great Britain.

    _In-day_ values are PV generation estimates for the current day,
    while _day-after_ values are
    updated PV generation truths for the previous day along with
    _in-day_ estimates for the current day.

    If nothing is set for the _regime_ parameter, the route will return
    _in-day_ values for the current day.

    #### Parameters
    - **regime**: can choose __in-day__ or __day-after__

    """
    logger.info(f"Get national PV Live estimates values " f"for regime {regime} for  {user}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=0, regime=regime
    )
