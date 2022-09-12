import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast, GSPYield
from sqlalchemy.orm.session import Session

from database import (
    get_latest_national_forecast_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
)

logger = logging.getLogger(__name__)


router = APIRouter()
NationalYield = GSPYield

# corresponds to API route /v0/solar/GB/national/forecast/
@router.get("/national/forecast", response_model=Forecast)
async def get_nationally_aggregated_forecasts(
    session: Session = Depends(get_session),
) -> Forecast:
    """### Returns a national aggregate solar PV energy forecast

    The return object is a forecast object.

    This route aggregrates data from all GSP forecasts and creates an 8-hour solar energy
    generation forecast  in 30-minute interval for all of GB.

    See __Forecast__ and __ForecastValue__ schemas for metadata descriptions.

    """

    logger.debug("Get national forecasts")
    return get_latest_national_forecast_from_database(session=session)

# corresponds to API route /v0/solar/GB/national/pvlive/, getting PV_Live NationalYield for GB
@router.get("/national/pvlive/", response_model=List[NationalYield])
async def get_national_pvlive(
    regime: Optional[str] = None, session: Session = Depends(get_session)
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

    logger.info(f"Get national PV Live estimates values for regime {regime}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=0, regime=regime
    )