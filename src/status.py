"""Get Status from database """
import os
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from nowcasting_datamodel.models import ForecastSQL, Status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.session import Session

from cache import cache_response
from database import get_latest_status_from_database, get_session, save_api_call_to_db
from utils import limiter, N_CALLS_PER_HOUR

logger = structlog.stdlib.get_logger()

router = APIRouter()

forecast_error_hours = float(os.getenv("FORECAST_ERROR_HOURS", 2.0))


@router.get("/status", response_model=Status)
@cache_response
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def get_status(request: Request, session: Session = Depends(get_session)) -> Status:
    """### Get status for the database and forecasts

    Occasionally there may be a small problem or interruption with the forecast. This
    route is where the OCF team communicates the forecast status to users.

    """
    logger.debug("Get status")
    return get_latest_status_from_database(session=session)


@router.get("/check_last_forecast_run", include_in_schema=False)
@limiter.limit(f"{N_CALLS_PER_HOUR}/hour")
def check_last_forecast(request: Request, session: Session = Depends(get_session)) -> datetime:
    """Check to that a forecast has run with in the last 2 hours"""

    save_api_call_to_db(session=session, request=request)

    logger.debug("Check to see when the last forecast run was ")

    query = session.query(ForecastSQL)
    query = query.order_by(ForecastSQL.created_utc.desc())
    query = query.limit(1)

    try:
        forecast = query.one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="There are no forecasts")

    if forecast.forecast_creation_time <= datetime.now(tz=timezone.utc) - timedelta(
        hours=forecast_error_hours
    ):
        raise HTTPException(
            status_code=404,
            detail=f"The last forecast is more than {forecast_error_hours} hours ago. "
            f"It was made at {forecast.forecast_creation_time}",
        )

    logger.debug(f"Last forecast time was {forecast.forecast_creation_time}")
    return forecast.forecast_creation_time
