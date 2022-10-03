"""National API routes"""
import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import Forecast, ForecastValue, GSPYield
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user

from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
)

logger = logging.getLogger(__name__)


router = APIRouter()
NationalYield = GSPYield


@router.get(
    "/forecast",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
async def get_national_forecast(
    session: Session = Depends(get_session),
    historic: Optional[bool] = False,
    only_forecast_values: Optional[bool] = False,
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> Union[Forecast, List[ForecastValue]]:
    """Get the National Forecast

    This route aggregrates data from all GSP forecasts and creates an 8-hour solar energy
    generation forecast  in 30-minute interval for all of GB.

    1. Get __recent solar forecast__ for the UK for today and yesterday
    with system details.
        - The return object is a solar forecast with forecast details.
        -The forecast object is returned with expected megawatt generation for the UK
        for the upcoming 8 hours at every 30-minute interval (targetTime).
        - Set __only_forecast_values__ ==> FALSE
        - Setting __historic__ parameter to TRUE returns an object with data
        from yesterday and today

    2. Get __ONLY__ forecast values for solar national forecast.
        - Set __only_forecast_values__ to TRUE
        - Setting a __forecast_horizon_minutes__ parameter retrieves the latest forecast
        a given set of minutes before the target time.
        - Return object is a simplified forecast object with __targetTimes__ and
        __expectedPowerGenerationMegawatts__ at 30-minute intervals.
        - NB: __historic__ parameter __will not__ work when __only_forecast_values__= TRUE

    Please see the __Forecast__ and __ForecastValue__ schema below for full metadata details.

    #### Parameters
    - historic: boolean => TRUE returns yesterday's forecasts in addition to today's forecast
    - only_forecast_values => TRUE returns solar national forecast values
    - forecast_horizon_minutes: optional forecast horizon in minutes (ex. 35 returns
    the latest forecast made 35 minutes before the target time)

    """

    logger.debug("Get national forecasts")

    if not only_forecast_values:
        logger.debug("Getting forecast.")
        full_forecast = get_forecasts_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=0,
            historic=historic,
        )

        logger.debug("Got forecast.")

        full_forecast.normalize()

        logger.debug("Normalized forecast.")

        logger.debug(
            f"Got national forecasts with {len(full_forecast.forecast_values)} forecast values"
        )
        return full_forecast

    else:

        national_forecast_values = get_latest_forecast_values_for_a_specific_gsp_from_database(
            session=session, gsp_id=0, forecast_horizon_minutes=forecast_horizon_minutes
        )

        logger.debug(f"Got national forecasts with {len(national_forecast_values)} forecast values")

    return national_forecast_values


# corresponds to API route /v0/solar/GB/national/pvlive/, getting PV_Live NationalYield for GB
@router.get("/pvlive", response_model=List[NationalYield], dependencies=[Depends(get_auth_implicit_scheme())])
async def get_national_pvlive(
    regime: Optional[str] = None, session: Session = Depends(get_session), user: Auth0User = Security(get_user()),
) -> List[NationalYield]:
    """### Get national PV_Live values for yesterday and today

    The return object is a series of real-time solar energy generation readings from PV_Live.

    PV_Live is Sheffield's API that reports real-time PV data. These readings are updated throughout
    the day, reporting the most accurate finalized readings the following day at 10:00 UTC.

    See the __GSPYield__ schema for metadata details.

    Check out [Sheffield Solar PV_Live](https://www.solarsheffield.ac.uk/pvlive/) for
    more details.

    The OCF Forecast is trying to predict the PV_Live 'day-after' value.

    This route has the __regime__ parameter that lets you look at values __in-day__ or
    __day-after__(most accurate reading). __Day-after__ values are updated __in-day__ values.
    __In-day__ gives you all the readings from the day before up to the most recent
    reported national yield. __Day_after__ reports all the readings from the previous day.
    For example, a day-after regime request made on 08/09/2022 returns updated national yield
    for 07/09/2022. The 08/09/2022 __day-after__ values then become available at 10:00 UTC
    on 09/09/2022.

    If regime is not specificied, the most up-to-date national yield is returned.

    #### Parameters
    - regime: can choose __in-day__ or __day-after__
    """

    logger.info(f"Get national PV Live estimates values "
                f"for regime {regime} for  {user}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=0, regime=regime
    )
