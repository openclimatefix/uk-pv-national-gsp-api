"""Get GSP boundary data from eso """
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from nowcasting_datamodel.models import Forecast, ForecastValue, ManyForecasts
from sqlalchemy.orm.session import Session

from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_latest_national_forecast_from_database,
    get_session,
)

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/all", response_model=ManyForecasts)
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


@router.get("/national", response_model=Forecast)
async def get_nationally_aggregated_forecasts(session: Session = Depends(get_session)) -> Forecast:
    """Get an aggregated forecast at the national level"""

    logger.debug("Get national forecasts")
    return get_latest_national_forecast_from_database(session=session)


@router.get("/{gsp_id}", response_model=Forecast)
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


@router.get("/forecast_values/{gsp_id}", response_model=List[ForecastValue])
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



