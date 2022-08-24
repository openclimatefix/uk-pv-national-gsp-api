""" Functions to read from the database and format """
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models import (
    Forecast,
    ForecastValue,
    GSPYield,
    Location,
    ManyForecasts,
    Status,
)
from nowcasting_datamodel.read.read import (
    get_all_gsp_ids_latest_forecast,
    get_all_locations,
    get_forecast_values,
    get_latest_forecast,
    get_latest_national_forecast,
    get_forecast_values_latest,
    get_latest_status,
    get_location,
    national_gb_label,
)
from nowcasting_datamodel.read.read_gsp import get_gsp_yield
from sqlalchemy.orm.session import Session

from utils import floor_30_minutes_dt

logger = logging.getLogger(__name__)


def get_latest_status_from_database(session: Session) -> Status:
    """Get latest status from database"""
    latest_status = get_latest_status(session)

    # convert to PyDantic object
    latest_status = Status.from_orm(latest_status)

    return latest_status


def get_forecasts_from_database(
    session: Session, historic: Optional[bool] = False
) -> ManyForecasts:
    """Get forecasts from database for all GSPs"""
    # get the latest forecast for all gsps.

    if historic:

        # get at most 2 days of data.
        yesterday_start_datetime = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
        yesterday_start_datetime = datetime.combine(yesterday_start_datetime, datetime.min.time())

        forecasts = get_all_gsp_ids_latest_forecast(
            session=session,
            start_target_time=yesterday_start_datetime,
            preload_children=True,
            historic=True,
        )
    else:
        # To speed up read time we only look at the last 12 hours of results, and take floor 30 mins
        yesterday_start_datetime = floor_30_minutes_dt(
            datetime.now(tz=timezone.utc) - timedelta(hours=12)
        )

        forecasts = get_all_gsp_ids_latest_forecast(
            session=session,
            start_created_utc=yesterday_start_datetime,
            start_target_time=yesterday_start_datetime,
            preload_children=True,
        )

    # change to pydantic objects
    if historic:
        forecasts = [Forecast.from_orm_latest(forecast) for forecast in forecasts]
    else:
        forecasts = [Forecast.from_orm(forecast) for forecast in forecasts]

    # return as many forecasts
    return ManyForecasts(forecasts=forecasts)


def get_forecasts_for_a_specific_gsp_from_database(
    session: Session, gsp_id, historic: Optional[bool] = False
) -> Forecast:
    """Get forecasts for on GSP from database"""

    yesterday_start_datetime = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
    yesterday_start_datetime = datetime.combine(yesterday_start_datetime, datetime.min.time())

    # get forecast from database
    forecast = get_latest_forecast(
        session=session,
        gsp_id=gsp_id,
        historic=historic,
        start_target_time=yesterday_start_datetime,
    )

    logger.debug("Found latest forecasts")

    if historic:
        return Forecast.from_orm_latest(forecast)
    else:
        return Forecast.from_orm(forecast)


def get_latest_forecast_values_for_a_specific_gsp_from_database(
    session: Session, gsp_id: int, forecast_horizon_minutes: Optional[int] = None
) -> List[ForecastValue]:
    """
    Get the forecast values for yesterday and today for one gsp

    :param session: sqlalchemy session
    :param gsp_id: gsp id, 0 is national
    :param forecast_horizon_minutes: Optional forecast horizon in minutes. I.e 35 minutes, means
        get the latest forecast made 35 minutes before the target time.
    :return: list of latest forecat values
    """

    yesterday_start_datetime = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
    yesterday_start_datetime = datetime.combine(yesterday_start_datetime, datetime.min.time())

    if forecast_horizon_minutes is None:
        return get_forecast_values_latest(
            session=session, gsp_id=gsp_id, start_datetime=yesterday_start_datetime
        )

    return get_forecast_values(
        session=session,
        gsp_id=gsp_id,
        start_datetime=yesterday_start_datetime,
        only_return_latest=True,
        forecast_horizon_minutes=forecast_horizon_minutes,
    )


def get_session():
    """Get database settion"""
    connection = DatabaseConnection(url=os.getenv("DB_URL", "not_set"))

    with connection.get_session() as s:
        yield s


def get_session_pv():
    """Get database sessions to pv database"""
    connection = DatabaseConnection(url=os.getenv("DB_URL_PV", "not_set"))

    with connection.get_session() as s:
        yield s


def get_latest_national_forecast_from_database(session: Session) -> Forecast:
    """Get the national level forecast from the database"""

    logger.debug("Getting latest national forecast")

    forecast = get_latest_national_forecast(session=session)
    logger.debug(forecast)
    return Forecast.from_orm(forecast)


def get_truth_values_for_a_specific_gsp_from_database(
    session: Session, gsp_id: int, regime: Optional[str] = "in-day"
) -> List[GSPYield]:
    """
    Get the truth value for one gsp for yesterday and today

    :param session: sql session
    :param gsp_id: gsp id
    :param regime: option for "in-day" or "day-after"
    :return: list of gsp yields
    """

    yesterday_start_datetime = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
    yesterday_start_datetime = datetime.combine(yesterday_start_datetime, datetime.min.time())

    return get_gsp_yield(
        session=session,
        gsp_ids=[gsp_id],
        start_datetime_utc=yesterday_start_datetime,
        regime=regime,
    )


def get_gsp_system(session: Session, gsp_id: Optional[int] = None) -> List[Location]:
    """
    Get gsp system details

    :param session:
    :param gsp_id: optional input. If None, get all systems
    :return:
    """

    if gsp_id is not None:

        # adjust label for nation location
        if gsp_id == 0:
            label = national_gb_label
        else:
            label = None

        # get one system
        gsp_systems = [get_location(session=session, gsp_id=gsp_id, label=label)]

    else:
        gsp_systems = get_all_locations(session=session)

    # change to pydantic object
    return [Location.from_orm(gsp_system) for gsp_system in gsp_systems]
