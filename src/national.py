"""National API routes"""
import os
from typing import List, Optional, Union

import structlog
from fastapi import APIRouter, Depends, Request, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import Forecast, GSPYield
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
)
from utils import NationalForecastValue, format_plevels

logger = structlog.stdlib.get_logger()


adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))
get_plevels = bool(os.getenv("GET_PLEVELS", True))

router = APIRouter()

NationalYield = GSPYield


@router.get(
    "/forecast",
    response_model=Union[Forecast, List[NationalForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_national_forecast(
    request: Request,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> Union[Forecast, List[NationalForecastValue]]:
    """Get the National Forecast

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

    """
    logger.debug("Get national forecasts")

    logger.debug("Getting forecast.")
    forecast_values = get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=0, forecast_horizon_minutes=forecast_horizon_minutes
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

    return national_forecast_values


# corresponds to API route /v0/solar/GB/national/pvlive/, getting PV_Live NationalYield for GB
@router.get(
    "/pvlive",
    response_model=List[NationalYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_national_pvlive(
    request: Request,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[NationalYield]:
    """### Get national PV_Live values for yesterday and/or today

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
