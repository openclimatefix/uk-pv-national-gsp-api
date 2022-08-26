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


def get_gsp_boundaries_from_eso_wgs84() -> gpd.GeoDataFrame:
    """Get GSP boundaries in lat/lon format (EPSG:4326)"""

    # get gsp boundaries
    boundaries = get_gsp_metadata_from_eso()

    # change to lat/lon - https://epsg.io/4326
    boundaries = boundaries.to_crs(4326)

    # fill nans
    boundaries = boundaries.fillna("")

    return boundaries


@router.get("/forecast/all", response_model=ManyForecasts)
async def get_all_available_forecasts(
    normalize: Optional[bool] = False,
    historic: Optional[bool] = False,
    session: Session = Depends(get_session),
) -> ManyForecasts:
    """Get the latest information for all available forecasts

    There is an option to normalize the forecasts by gsp capacity
    There is also an option to pull historic data.
        This will the load the latest forecast value for each target time.
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
    """Get an aggregated forecast at the national level"""

    logger.debug("Get national forecasts")
    return get_latest_national_forecast_from_database(session=session)


@router.get("/forecast/{gsp_id}", response_model=Forecast)
async def get_forecasts_for_a_specific_gsp(
    gsp_id: int,
    session: Session = Depends(get_session),
    historic: Optional[bool] = False,
) -> Forecast:
    """
    Get one forecast for a specific GSP id.

     This gets the latest forecast for each target time for yesterday and toady.

    :param gsp_id: The gsp id of the forecast you want
    :param session: sql session (this is done automatically)
    :param historic: There is an option to get historic forecast also.
    :return: Forecast object
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} with {historic=}")

    return get_forecasts_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        historic=historic,
    )


@router.get("/forecast/forecast_values/{gsp_id}", response_model=List[ForecastValue])
async def get_latest_forecasts_for_a_specific_gsp(
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
) -> List[ForecastValue]:
    """Get the latest forecast values for a specific GSP id for today and yesterday

    :param gsp_id: The gsp id of the forecast you want
    :param session: sql session (this is done automatically)
    :param forecast_horizon_minutes: Optional forecast horizon in minutes. I.e 35 minutes, means
        get the latest forecast made 35 minutes before the target time.
    """

    logger.info(f"Get forecasts for gsp id {gsp_id} with {forecast_horizon_minutes=}")

    return get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, forecast_horizon_minutes=forecast_horizon_minutes
    )


@router.get("/pvlive/{gsp_id}/", response_model=List[GSPYield])
async def get_truths_for_a_specific_gsp(
    gsp_id: int, regime: Optional[str] = None, session: Session = Depends(get_session)
) -> List[GSPYield]:
    """Get PV live values for a specific GSP id, for yesterday and today

    See https://www.solar.sheffield.ac.uk/pvlive/ for more details.
    Regime can "in-day" or "day-after",
    as new values are calculated around midnight when more data is available.
    If regime is not specific, the latest gsp yield is loaded.

    The OCF Forecast is trying to predict the PV live 'day-after' value.
    """

    logger.info(f"Get PV Live estimates values for gsp id {gsp_id} and regime {regime}")

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )


@router.get("/gsp_boundaries")
async def get_gsp_boundaries() -> dict:
    """Get one gsp boundary for a specific GSP id

    This is a wrapper around the dataset in
    'https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points'

    The returned object is in EPSG:4326 i.e latitude and longitude
    """

    logger.info("Getting all GSP boundaries")

    json_string = get_gsp_boundaries_from_eso_wgs84().to_json()

    json.loads(json_string)

    return json.loads(json_string)


@router.get("/gsp_systems", response_model=List[Location])
async def get_systems(
    session: Session = Depends(get_session), gsp_id: Optional[int] = None
) -> List[Location]:
    """
    Get gsp system details.

    Provide gsp_id to just return one gsp system, otherwise all are returned
    """

    logger.info(f"Get GSP systems for {gsp_id=}")

    return get_gsp_system(session=session, gsp_id=gsp_id)
