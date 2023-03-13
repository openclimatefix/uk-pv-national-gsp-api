"""Get Status from database """
import logging
import os

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from nowcasting_datamodel.models import Status, ForecastSQL
from sqlalchemy.orm.session import Session
from sqlalchemy.exc import NoResultFound

from cache import cache_response
from database import get_latest_status_from_database, get_session

logger = logging.getLogger(__name__)


router = APIRouter()

forecast_error_hours = float(os.getenv('FORECAST_ERROR_HOURS', 2.0))


@router.get("/status", response_model=Status)
@cache_response
def get_status(session: Session = Depends(get_session)) -> Status:
    """### Get status for solar forecasts

    (might be good to explain this a bit more)

    """

    logger.debug("Get status")
    return get_latest_status_from_database(session=session)


@router.get("/check_last_forecast_run", include_in_schema=False)
def check_last_forecast(session: Session = Depends(get_session)) -> datetime:
    """Check to that a forecast has run with in the last 2 hours"""

    logger.debug("Check to see when the last forecast run was ")

    query = session.query(ForecastSQL)
    query = query.order_by(ForecastSQL.created_utc.desc())

    try:
        forecast = query.one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="There are no forecasts")

    if forecast.forecast_creation_time <= datetime.now(tz=timezone.utc) - timedelta(hours=forecast_error_hours):
        raise HTTPException(
            status_code=404,
            detail=f"The last forecast is more than {forecast_error_hours} hours ago. "
            f"It was made at {forecast.forecast_creation_time}",
        )

    return forecast.forecast_creation_time
