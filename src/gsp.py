"""Get GSP boundary data from eso """
import json
import logging
from typing import List, Optional

import geopandas as gpd
from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast, ForecastValue, GSPYield, Location, ManyForecasts
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso
from sqlalchemy.orm.session import Session

from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_gsp_system,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_latest_national_forecast_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
)

logger = logging.getLogger(__name__)


router = APIRouter()
NationalYield = GSPYield


def get_gsp_boundaries_from_eso_wgs84() -> gpd.GeoDataFrame:
    """Get GSP boundaries in lat/lon format (EPSG:4326)"""

    # get gsp boundaries
    boundaries = get_gsp_metadata_from_eso()

    # change to lat/lon - https://epsg.io/4326
    boundaries = boundaries.to_crs(4326)

    # fill nans
    boundaries = boundaries.fillna("")

    return boundaries


@router.get("/forecast/one_gsp/{gsp_id}", response_model=Forecast)
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

    return get_forecasts_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        historic=historic,
    )


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
        session=session, gsp_id=gsp_id, forecast_horizon_minutes=forecast_horizon_minutes
    )


@router.get("/pvlive/one_gsp/{gsp_id}/", response_model=List[GSPYield])
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


@router.get("/forecast/all", response_model=ManyForecasts)
async def get_all_available_forecasts(
    normalize: Optional[bool] = False,
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
    - normalize: boolean => TRUE returns a value for _expectedPowerGenerationNormalized__,
        which in decimals is the percent of __installedCapacityMw__ (installed PV megawatt capacity)
        being forecasted / FALSE returns "null"
    - historic: boolean => TRUE returns the forecasts of yesterday along with today's
        forecasts for all GSPs
    """

    logger.info(f"Get forecasts for all gsps. The options are  {normalize=} and {historic=}")

    forecasts = get_forecasts_from_database(session=session, historic=historic)

    logger.debug(f"Normalizing {normalize}")
    if normalize:
        forecasts.normalize()
        logger.debug("Normalizing: done")

    return forecasts


@router.get("/forecast/national", response_model=Forecast)
async def get_nationally_aggregated_forecasts(session: Session = Depends(get_session)) -> Forecast:
    """### Returns a national aggregate solar PV energy forecast

    The return object is a forecast object.

    This route aggregrates data from all GSP forecasts and creates an 8-hour solar energy
    generation forecast  in 30-minute interval for all of GB.

    See __Forecast__ and __ForecastValue__ schemas for metadata descriptions.

    """

    logger.debug("Get national forecasts")
    return get_latest_national_forecast_from_database(session=session)


@router.get("/gsp_boundaries")
async def get_gsp_boundaries() -> dict:
    """### Get one GSP boundary for a specific GSP

    This route is still under construction...

    [This is a wrapper around the dataset]
    (https://data.nationalgrideso.com/systemgis-boundaries-for-gb-grid-supply-points).

    Returns an object that is in EPSG:4326 (ie. latitude & longitude coordinates).

    """

    logger.info("Getting all GSP boundaries")

    json_string = get_gsp_boundaries_from_eso_wgs84().to_json()

    json.loads(json_string)

    return json.loads(json_string)


@router.get("/gsp_systems", response_model=List[Location])
async def get_systems(
    session: Session = Depends(get_session), gsp_id: Optional[int] = None
) -> List[Location]:
    """### Get system details for a single GSP or all GSPs

    Returns an object with the system details of a given GSP using the
    gsp_id parameter.

    Provide one gsp_id to return system details for that GSP, otherwise details for ALL
    grid systems will be returned.

    Please see __Location__ schema for metadata details.

    #### Parameters
    - gsp_id: gsp_id of the requested system
    - NB: If no parameter is entered, system details for all 300+ GSPs are returned.

    """

    logger.info(f"Get GSP systems for {gsp_id=}")

    return get_gsp_system(session=session, gsp_id=gsp_id)
