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


# define route => /v0/solar/GB/gsp/forecast/{gsp_id}/{only_values} or other filter parameters
# get latest gsp with only values
# if getting latest
#  async def get latest only values
#    logger.info(f"Get forecasts for gsp id {gsp_id} with {forecast_horizon_minutes=}")

    # # return get_latest_forecast_values_for_a_specific_gsp_from_database(
    #     session=session,
    #     gsp_id=gsp_id,
    #     forecast_horizon_minutes=forecast_horizon_minutes,
    # )

@router.get("/forecast/{gsp_id}/{only_values}", response_model= Union[Forecast, List[Forecast]] )
async def get_forecasts_for_a_specific_gsp(
    gsp_id: int,
    session: Session = Depends(get_session),
    historic: Optional[bool] = False,
    only_values: Optional[bool] = False,
    forecast_horizon_minutes: Optional[int] = None,
) -> Union[Forecast, List[Forecast]]:
    """### Get one forecast for a specific GSP

    The return object is a solar forecast with GSP system details.

    The forecast object is returned with expected megawatt generation at a specific GSP
    for the upcoming 8 hours at every 30-minute interval (targetTime).

    Setting history to TRUE on this route will return readings from yesterday and today
    for the given GSP.

    Please refer to the __Forecast__ and __ForecastValue__ schemas below for metadata definitions.

    #### Parameters
    - gsp_id: gsp_id of the desired forecast
    - historic: boolean => TRUE returns yesterday's forecasts in addition to today's forecast
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} with {historic=} or {only_values} and {forecast_horizon_minutes=}")
    
    if only_values is False:
        full_forecast = get_forecasts_for_a_specific_gsp_from_database(
            session=session,
            gsp_id=gsp_id,
            historic=historic,
            )

        full_forecast.normalize()
        
        return full_forecast

    print('this is working')
        

    only_values_forecast = get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        forecast_horizon_minutes=forecast_horizon_minutes,
    )
    
    return only_values_forecast




    


@router.get("/forecast/{gsp_id}", response_model= Forecast )
async def get_forecasts_for_a_specific_gsp(
    gsp_id: int,
    session: Session = Depends(get_session),
    historic: Optional[bool] = False,
) -> Forecast:
    """### Get one forecast for a specific GSP

    The return object is a solar forecast with GSP system details.

    The forecast object is returned with expected megawatt generation at a specific GSP
    for the upcoming 8 hours at every 30-minute interval (targetTime).

    Setting history to TRUE on this route will return readings from yesterday and today
    for the given GSP.

    Please refer to the __Forecast__ and __ForecastValue__ schemas below for metadata definitions.

    #### Parameters
    - gsp_id: gsp_id of the desired forecast
    - historic: boolean => TRUE returns yesterday's forecasts in addition to today's forecast
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} with {historic=}")

    forecast = get_forecasts_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        historic=historic,
    )

    forecast.normalize()

    return forecast


# corresponds to API route /v0/solar/GB/gsp/forecast/{gsp_id}/{only_values}
# or other filter parameters
@router.get("/forecast/latest/{gsp_id}", response_model=List[ForecastValue])
async def get_latest_forecasts_for_a_specific_gsp(
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
) -> List[ForecastValue]:
    """### Gets the latest forecasts for a specific GSP for today and yesterday

    The object returned is a solar forecast for the GSP without GSP system details.

    This route returns a simplified forecast object with __targetTimes__ and
    __expectedPowerGenerationMegawatts__ at 30-minute intervals for
    the given GSP. The __forecast_horizon_minutes__ parameter
    retrieves the latest forecast a given set of minutes before the target time.

    Please see the __ForecastValue__ schema below for full metadata details.

    #### Parameters
    - gsp_id: gsp_id of the requested forecast
    - forecast_horizon_minutes: optional forecast horizon in minutes (ex. 35 returns
    the latest forecast made 35 minutes before the target time)
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} with {forecast_horizon_minutes=}")

    return get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        forecast_horizon_minutes=forecast_horizon_minutes,
    )


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
