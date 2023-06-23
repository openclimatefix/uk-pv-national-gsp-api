"""Get GSP boundary data from eso """
from typing import List, Optional, Union

import structlog
from fastapi import APIRouter, Depends, Request, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import (
    Forecast,
    ForecastValue,
    GSPYield,
    LocationWithGSPYields,
    ManyForecasts,
)
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
    get_truth_values_for_all_gsps_from_database,
    save_api_call_to_db,
)

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
    """### Get the latest information for all available forecasts for all GSPs

    The return object contains a forecast object with system details for all National Grid GSPs.

    This request may take a longer time to load because a lot of data is being pulled from the
    database.

    #### Parameters
    - **historic**: boolean => TRUE returns the forecasts of yesterday along with today's
    forecasts for all GSPs

    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(f"Get forecasts for all gsps. The option is {historic=} for user {user}")

    forecasts = get_forecasts_from_database(session=session, historic=historic)

    forecasts.normalize()

    return forecasts


@router.get(
    "/forecast/{gsp_id}",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_forecasts_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    session: Session = Depends(get_session),
    historic: Optional[bool] = False,
    only_forecast_values: Optional[bool] = False,
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> Union[Forecast, List[ForecastValue]]:
    """### Get recent forecast values for a specific GSP

    #### Parameters
    - **gsp_id**: gsp_id of the desired forecast
    - **forecast_horizon_minutes**: optional forecast horizon in minutes (ex. 60
    returns the latest forecast made 60 minutes before the target time)
    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(f"Get forecasts for gsp id {gsp_id} forecast of forecast with only values.")
    logger.info(f"This is for user {user}")

    if only_forecast_values is False:
        logger.debug("Getting forecast.")
        full_forecast = get_forecasts_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=gsp_id,
            historic=historic,
        )

        logger.debug("Got forecast.")

        full_forecast.normalize()

        logger.debug(f'{"Normalized forecast."}')
        return full_forecast

    else:
        logger.debug("Getting forecast values only.")

        forecast_only = get_latest_forecast_values_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=gsp_id,
            forecast_horizon_minutes=forecast_horizon_minutes,
        )

        logger.debug("Got forecast values only!!!")

        return forecast_only


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
    """### Get PV_Live values for all GSPs for yesterday and/or today

    The return object is a series of real-time PV generation estimates or truth values
    from PV_Live for all GSPs.

    Setting the __regime__ parameter to __day-after__ includes
    the previous day's truth values for the GSPs. The default is __in-day__.

    #### Parameters
    - **gsp_id**: gsp_id of the requested forecast
    - **regime**: can choose __in-day__ or __day-after__
    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(f"Get PV Live estimates values for all gsp id and regime {regime} for user {user}")

    return get_truth_values_for_all_gsps_from_database(session=session, regime=regime)


# corresponds to API route /v0/solar/GB/gsp/pvlive/{gsp_id}
@router.get(
    "/pvlive/{gsp_id}",
    response_model=List[GSPYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
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
    from PV_Live for a single GSP.

    If regime is not specified, the most up-to-date GSP yield is returned.

    #### Parameters
    - **gsp_id**: gsp_id of the requested forecast
    - **regime**: can choose __in-day__ or __day-after__
    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(
        f"Get PV Live estimates values for gsp id {gsp_id} " f"and regime {regime} for user {user}"
    )

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )
