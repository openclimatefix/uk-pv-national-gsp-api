"""Get GSP boundary data from eso """

import os
from datetime import datetime, timezone
from typing import List, Optional, Union

import structlog
from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_forecasts_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
    get_truth_values_for_all_gsps_from_database,
)
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Request, Security, status
from fastapi.responses import Response
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import Forecast, ForecastValue, ManyForecasts
from pydantic_models import (
    GSPYield,
    GSPYieldGroupByDatetime,
    LocationWithGSPYields,
    OneDatetimeManyForecastValues,
)
from sqlalchemy.orm.session import Session
from utils import (
    N_CALLS_PER_HOUR,
    N_SLOW_CALLS_PER_MINUTE,
    floor_30_minutes_dt,
    format_datetime,
    limiter,
)

GSP_TOTAL = 317


logger = structlog.stdlib.get_logger()
adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))
load_dotenv()


router = APIRouter(
    tags=["GSP"],
)
NationalYield = GSPYield


# corresponds to route /v0/solar/GB/gsp/forecast/all/
@router.get(
    "/forecast/all/",
    response_model=Union[ManyForecasts, List[OneDatetimeManyForecastValues]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
@limiter.limit(f"{N_SLOW_CALLS_PER_MINUTE}/minute")
def get_all_available_forecasts(
    request: Request,
    historic: Optional[bool] = True,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
    start_datetime_utc: Optional[str] = None,
    end_datetime_utc: Optional[str] = None,
    compact: Optional[bool] = False,
    gsp_ids: Optional[str] = None,
    creation_limit_utc: Optional[str] = None,
) -> Union[ManyForecasts, List[OneDatetimeManyForecastValues]]:
    """### Get all forecasts for all GSPs

    The return object contains a forecast object with system details and
    forecast values for all GSPs.

    This request may take a longer time to load because a lot of data is being
    pulled from the database.

    If _compact_ is set to true, the response will be a list of GSPGenerations objects.
    This return object is significantly smaller, but less readable.

    _gsp_ids_ is a list of integers that correspond to the GSP ids.
    If this is 1,2,3,4 the response will only contain those GSPs.

    #### Parameters
    - **historic**: boolean that defaults to `true`, returning yesterday's and
    today's forecasts for all GSPs
    - **start_datetime_utc**: optional start datetime for the query. e.g '2023-08-12 10:00:00+00:00'
    - **end_datetime_utc**: optional end datetime for the query. e.g '2023-08-12 14:00:00+00:00'
    """

    if isinstance(gsp_ids, str):
        gsp_ids = [int(gsp_id) for gsp_id in gsp_ids.split(",")]
        if gsp_ids == "":
            gsp_ids = None

    logger.info(f"Get forecasts for all gsps. The option is {historic=} for user {user}")

    start_datetime_utc = format_datetime(start_datetime_utc)
    end_datetime_utc = format_datetime(end_datetime_utc)
    creation_limit_utc = format_datetime(creation_limit_utc)

    # by default, don't get any data in the past if more than one gsp
    if start_datetime_utc is None and (gsp_ids is None or len(gsp_ids) > 1):
        start_datetime_utc = floor_30_minutes_dt(datetime.now(tz=timezone.utc))

    forecasts = get_forecasts_from_database(
        session=session,
        historic=historic,
        start_datetime_utc=start_datetime_utc,
        end_datetime_utc=end_datetime_utc,
        compact=compact,
        gsp_ids=gsp_ids,
        creation_utc_limit=creation_limit_utc,
    )

    logger.info(f"Got forecasts for all gsps. The option is {historic=} for user {user}")

    if not compact:
        logger.info("Normalizing forecasts")
        forecasts.normalize()
        logger.info("Normalized forecasts")

        logger.info(
            f"Got {len(forecasts.forecasts)} forecasts for all gsps. "
            f"The option is {historic=} for user {user}"
        )

        # adjust gsp_id 0
        idx = [
            i for i, forecasts in enumerate(forecasts.forecasts) if forecasts.location.gsp_id == 0
        ]
        if len(idx) > 0:
            logger.info(f"Adjusting forecast values for gsp id 0, {adjust_limit}")
            forecasts.forecasts[idx[0]] = forecasts.forecasts[idx[0]].adjust(limit=adjust_limit)
        else:
            logger.debug("Not running adjuster as no gsp_id==0 were found")

    return forecasts


@router.get(
    "/forecast/{gsp_id}",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
    include_in_schema=False,
    responses={status.HTTP_204_NO_CONTENT: {"model": None}},
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_forecasts_for_a_specific_gsp_old_route(
    request: Request,
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> Union[Forecast, List[ForecastValue]]:
    """Redirects old API route to new route /v0/solar/GB/gsp/{gsp_id}/forecast"""

    return get_forecasts_for_a_specific_gsp(
        request=request,
        gsp_id=gsp_id,
        session=session,
        forecast_horizon_minutes=forecast_horizon_minutes,
        user=user,
    )


@router.get(
    "/{gsp_id}/forecast",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
    responses={status.HTTP_204_NO_CONTENT: {"model": None}},
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_forecasts_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
    start_datetime_utc: Optional[str] = None,
    end_datetime_utc: Optional[str] = None,
    creation_limit_utc: Optional[str] = None,
) -> Union[Forecast, List[ForecastValue]]:
    """### Get recent forecast values for a specific GSP

    This route returns the most recent forecast for each _target_time_ for a
    specific GSP.

    The _forecast_horizon_minutes_ parameter allows
    a user to query for a forecast that is made this number, or horizon, of
    minutes before the _target_time_.

    For example, if the target time is 10am today, the forecast made at 2am
    today is the 8-hour forecast for 10am, and the forecast made at 6am for
    10am today is the 4-hour forecast for 10am.

    #### Parameters
    - **gsp_id**: *gsp_id* of the desired forecast
    - **forecast_horizon_minutes**: optional forecast horizon in minutes (ex. 60
    - **start_datetime_utc**: optional start datetime for the query.
    - **end_datetime_utc**: optional end datetime for the query.
    - **creation_utc_limit**: optional, only return forecasts made before this datetime.
    returns the latest forecast made 60 minutes before the target time)
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} forecast of forecast with only values.")
    logger.info(f"This is for user {user}")

    start_datetime_utc = format_datetime(start_datetime_utc)
    end_datetime_utc = format_datetime(end_datetime_utc)
    creation_limit_utc = format_datetime(creation_limit_utc)

    if gsp_id > GSP_TOTAL:
        return Response(None, status.HTTP_204_NO_CONTENT)

    forecast_values_for_specific_gsp = get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        forecast_horizon_minutes=forecast_horizon_minutes,
        start_datetime_utc=start_datetime_utc,
        end_datetime_utc=end_datetime_utc,
        creation_utc_limit=creation_limit_utc,
    )

    if gsp_id == 0:
        forecast_values_for_specific_gsp = [
            f.adjust(limit=adjust_limit) for f in forecast_values_for_specific_gsp
        ]

    logger.debug("Got forecast values for a specific gsp.")

    return forecast_values_for_specific_gsp


# corresponds to API route /v0/solar/GB/gsp/pvlive/all
@router.get(
    "/pvlive/all",
    response_model=Union[List[LocationWithGSPYields], List[GSPYieldGroupByDatetime]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_truths_for_all_gsps(
    request: Request,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
    start_datetime_utc: Optional[str] = None,
    end_datetime_utc: Optional[str] = None,
    compact: Optional[bool] = False,
    gsp_ids: Optional[str] = None,
) -> Union[List[LocationWithGSPYields], List[GSPYieldGroupByDatetime]]:
    """### Get PV_Live values for all GSPs for yesterday and today

    The return object is a series of real-time PV generation estimates or
    truth values from __PV_Live__ for all GSPs.

    Setting the _regime_ parameter to _day-after_ includes
    the previous day's truth values for the GSPs.

    If _regime_ is not specified, the parameter defaults to _in-day_.

    If _compact_ is set to true, the response will be a list of GSPGenerations objects.
    This return object is significantly smaller, but less readable.

    #### Parameters
    - **regime**: can choose __in-day__ or __day-after__
    - **start_datetime_utc**: optional start datetime for the query.
    - **end_datetime_utc**: optional end datetime for the query.
    """

    if isinstance(gsp_ids, str):
        gsp_ids = [int(gsp_id) for gsp_id in gsp_ids.split(",")]

    logger.info(f"Get PV Live estimates values for all gsp id and regime {regime} for user {user}")

    start_datetime_utc = format_datetime(start_datetime_utc)
    end_datetime_utc = format_datetime(end_datetime_utc)

    return get_truth_values_for_all_gsps_from_database(
        session=session,
        regime=regime,
        start_datetime_utc=start_datetime_utc,
        end_datetime_utc=end_datetime_utc,
        compact=compact,
        gsp_ids=gsp_ids,
    )


@router.get(
    "/pvlive/{gsp_id}",
    response_model=List[GSPYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
    include_in_schema=False,
    responses={status.HTTP_204_NO_CONTENT: {"model": None}},
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_truths_for_a_specific_gsp_old_route(
    request: Request,
    gsp_id: int,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[GSPYield]:
    """Redirects old API route to new route /v0/solar/GB/gsp/{gsp_id}/pvlive"""

    return get_truths_for_a_specific_gsp(
        request=request,
        gsp_id=gsp_id,
        regime=regime,
        session=session,
        user=user,
    )


# corresponds to API route /v0/solar/GB/gsp/{gsp_id}/pvlive
@router.get(
    "/{gsp_id}/pvlive",
    response_model=List[GSPYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
    responses={status.HTTP_204_NO_CONTENT: {"model": None}},
)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_truths_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    regime: Optional[str] = None,
    start_datetime_utc: Optional[str] = None,
    end_datetime_utc: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[GSPYield]:
    """### Get PV_Live values for a specific GSP for yesterday and today

    The return object is a series of real-time solar energy generation
    from __PV_Live__ for a single GSP.

    Setting the _regime_ parameter to _day-after_ includes
    the previous day's truth values for the GSPs.

    If _regime_ is not specified, the parameter defaults to _in-day_.

    #### Parameters
    - **gsp_id**: _gsp_id_ of the requested forecast
    - **regime**: can choose __in-day__ or __day-after__
    - **start_datetime_utc**: optional start datetime for the query.
    - **end_datetime_utc**: optional end datetime for the query.
    If not set, defaults to N_HISTORY_DAYS env var, which if not set defaults to yesterday.
    """

    logger.info(
        f"Get PV Live estimates values for gsp id {gsp_id} " f"and regime {regime} for user {user}"
    )

    start_datetime_utc = format_datetime(start_datetime_utc)
    end_datetime_utc = format_datetime(end_datetime_utc)

    if gsp_id > GSP_TOTAL:
        return Response(None, status.HTTP_204_NO_CONTENT)

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        regime=regime,
        start_datetime=start_datetime_utc,
        end_datetime=end_datetime_utc,
    )
