"""Get GSP boundary data from eso """
import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast, ForecastValue, GSPYield, ManyForecasts
from sqlalchemy.orm.session import Session

from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
)

logger = logging.getLogger(__name__)


router = APIRouter()
NationalYield = GSPYield


# corresponds to route /v0/solar/GB/gsp/forecast/all
@router.get("/forecast/all/", response_model=ManyForecasts)
async def get_all_available_forecasts(
    historic: Optional[bool] = False,
    session: Session = Depends(get_session),
) -> ManyForecasts:
    """### Get the latest information for ALL available forecasts for ALL GSPs

    The return object contains a forecast object with system details for all National Grid GSPs.

    See __Forecast__ and __ForecastValue__ schema for metadata details.

    This request may take a longer time to load because a lot of data is being pulled from the
    database.

    This route returns forecasts objects from all available GSPs with an option to normalize
    the forecasts by GSP installed capacity (installedCapacityMw). Normalization returns a
    decimal value equal to _expectedPowerGenerationMegawatts_ divided by
    __installedCapacityMw__ for the GSP.

    There is also the option to pull forecast history from yesterday.


    #### Parameters
    - historic: boolean => TRUE returns the forecasts of yesterday along with today's
    forecasts for all GSPs
    """

    logger.info(f"Get forecasts for all gsps. The option is {historic=}")

    forecasts = get_forecasts_from_database(session=session, historic=historic)

    forecasts.normalize()

    return forecasts


@router.get("/forecast/{gsp_id}", response_model=Union[Forecast, List[ForecastValue]])
async def get_forecasts_for_a_specific_gsp(
    gsp_id: int,
    session: Session = Depends(get_session),
    historic: Optional[bool] = False,
    only_forecast_values: Optional[bool] = False,
    forecast_horizon_minutes: Optional[int] = None,
) -> Union[Forecast, List[ForecastValue]]:
    """### Get the most recent full forecast or a __values only__ only forecast 

    This route comes with the following options: 

    1. Get __recent forecast__ for a specific GSP with system details.
        - The return object is a solar forecast with GSP system details.
        -The forecast object is returned with expected megawatt generation at 
        a specific GSP
        for the upcoming 8 hours at every 30-minute interval (targetTime).
        - Set __only_forecast_values__ ==> FALSE 
        - Setting __historic__ parameter to TRUE returns an object with data 
        from yesterday and today
        for the given GSP

    2. Get __ONLY__ forecast values for a specific GSP.
        - Set __only_forecast_values__ to TRUE 
        - Setting a __forecast_horizon_minutes__ parameter retrieves the latest forecast 
        a given set of minutes before the target time.
        - Return object is a simplified forecast object with __targetTimes__ and
        __expectedPowerGenerationMegawatts__ at 30-minute intervals for the given GSP.
        - NB: __historic__ parameter __will not__ work when __only_forecast_values__= TRUE

    Please see the __Forecast__ and __ForecastValue__ schema below for full metadata details.

    #### Parameters
    - gsp_id: gsp_id of the desired forecast
    - historic: boolean => TRUE returns yesterday's forecasts in addition to today's forecast
    - only_forecast_values => TRUE returns solar forecast for the GSP without system details
    - forecast_horizon_minutes: optional forecast horizon in minutes (ex. 35 returns
    the latest forecast made 35 minutes before the target time)
    """

    logger.info(f'{"Get forecasts for gsp id {gsp_id} forecast of forecast with only values."}')

    if only_forecast_values is False:
        logger.debug(f'{"Getting forecast."}')
        full_forecast = get_forecasts_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=gsp_id,
            historic=historic,
        )

        logger.debug(f'{"Got forecast."}')

        full_forecast.normalize()

        logger.debug(f'{"Normalized forecast."}')
        return full_forecast

    else:

        logger.debug(f'{"Getting forecast values only."}')

        forecast_only = get_latest_forecast_values_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=gsp_id,
            forecast_horizon_minutes=forecast_horizon_minutes,
        )

        logger.debug(f'{"Got forecast values only!!!"}')

        return forecast_only


# corresponds to API route /v0/solar/GB/gsp/pvlive/{gsp_id}
@router.get("/pvlive/{gsp_id}", response_model=List[GSPYield])
async def get_truths_for_a_specific_gsp(
    gsp_id: int, regime: Optional[str] = None, session: Session = Depends(get_session)
) -> List[GSPYield]:
    """### Get PV_Live values for a specific GSP for yesterday and today

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
    reported GSP yield. __Day_after__ reports all the readings from the previous day.
    For example, a day-after regime request made on 08/09/2022 returns updated GSP yield
    for 07/09/2022. The 08/09/2022 __day-after__ values then become available at 10:00 UTC
    on 09/09/2022.

    If regime is not specificied, the most up-to-date GSP yield is returned.

    #### Parameters
    - gsp_id: gsp_id of the requested forecast
    - regime: can choose __in-day__ or __day-after__
    """

    logger.info(f"Get PV Live estimates values for gsp id {gsp_id} and regime {regime}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )
