"""Get GSP boundary data from eso """
from typing import List, Optional, Union

import structlog
from fastapi import APIRouter, Depends, Request, Security, status
from fastapi.responses import Response
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import (
    Forecast,
    ForecastValue,
    ManyForecasts,
)
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_forecasts_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
    get_truth_values_for_all_gsps_from_database,
)
from pydantic_models import LocationWithGSPYields, GSPYield

GSP_TOTAL = 317


logger = structlog.stdlib.get_logger()


router = APIRouter()
NationalYield = GSPYield


# corresponds to route /v0/solar/GB/gsp/forecast/all
@router.get(
    "/forecast/all/",
    response_model=ManyForecasts,
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_all_available_forecasts(
    request: Request,
    historic: Optional[bool] = True,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> ManyForecasts:
    """### Get all forecasts for all GSPs

    The return object contains a forecast object with system details and
    forecast values for all GSPs.

    This request may take a longer time to load because a lot of data is being
    pulled from the database.

    #### Parameters
    - **historic**: boolean that defaults to `true`, returning yesterday's and
    today's forecasts for all GSPs
    """

    logger.info(f"Get forecasts for all gsps. The option is {historic=} for user {user}")

    forecasts = get_forecasts_from_database(session=session, historic=historic)

    forecasts.normalize()

    logger.info(f"Got {len(forecasts.forecasts)} forecasts for all gsps. The option is {historic=} for user {user}")

    return forecasts


@router.get(
    "/forecast/{gsp_id}",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
    include_in_schema=False,
    responses={status.HTTP_204_NO_CONTENT: {"model": None}},
)
@cache_response
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
def get_forecasts_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
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
    returns the latest forecast made 60 minutes before the target time)
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} forecast of forecast with only values.")
    logger.info(f"This is for user {user}")

    if gsp_id > GSP_TOTAL:
        return Response(None, status.HTTP_204_NO_CONTENT)

    forecast_values_for_specific_gsp = get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        forecast_horizon_minutes=forecast_horizon_minutes,
    )

    logger.debug("Got forecast values for a specific gsp.")

    return forecast_values_for_specific_gsp


# corresponds to API route /v0/solar/GB/gsp/pvlive/all
@router.get(
    "/pvlive/all",
    response_model=List[LocationWithGSPYields],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_truths_for_all_gsps(
    request: Request,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[LocationWithGSPYields]:
    """### Get PV_Live values for all GSPs for yesterday and today

    The return object is a series of real-time PV generation estimates or
    truth values from __PV_Live__ for all GSPs.

    Setting the _regime_ parameter to _day-after_ includes
    the previous day's truth values for the GSPs.

    If _regime_ is not specified, the parameter defaults to _in-day_.

    #### Parameters
    - **regime**: can choose __in-day__ or __day-after__
    """
    logger.info(f"Get PV Live estimates values for all gsp id and regime {regime} for user {user}")

    return get_truth_values_for_all_gsps_from_database(session=session, regime=regime)


@router.get(
    "/pvlive/{gsp_id}",
    response_model=List[GSPYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
    include_in_schema=False,
    responses={status.HTTP_204_NO_CONTENT: {"model": None}},
)
@cache_response
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
def get_truths_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    regime: Optional[str] = None,
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
    """

    logger.info(
        f"Get PV Live estimates values for gsp id {gsp_id} " f"and regime {regime} for user {user}"
    )

    if gsp_id > GSP_TOTAL:
        return Response(None, status.HTTP_204_NO_CONTENT)

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )
