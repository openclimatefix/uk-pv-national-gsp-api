""" Functions to read from the database and format data """

import abc
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Type, Union, cast

import structlog
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models import (
    APIRequestSQL,
    Forecast,
    ForecastValue,
    ForecastValueLatestSQL,
    ForecastValueSevenDaysSQL,
    ForecastValueSQL,
    GSPYieldSQL,
    Location,
    LocationSQL,
    ManyForecasts,
    Status,
    User,
)
from nowcasting_datamodel.read.read import (
    get_all_gsp_ids_latest_forecast,
    get_all_locations,
    get_forecast_values,
    get_forecast_values_latest,
    get_latest_forecast,
    get_latest_national_forecast,
    get_latest_status,
    get_location,
    national_gb_label,
)
from nowcasting_datamodel.read.read_gsp import get_gsp_yield_by_location
from nowcasting_datamodel.read.read_user import get_user as get_user_from_db
from nowcasting_datamodel.save.update import N_GSP
from pydantic_models import (
    GSPYield,
    GSPYieldGroupByDatetime,
    LocationWithGSPYields,
    OneDatetimeManyForecastValues,
    convert_forecasts_to_many_datetime_many_generation,
    convert_location_sql_to_many_datetime_many_generation,
)
from sqlalchemy import select
from sqlalchemy.orm.session import Session
from utils import filter_forecast_values, floor_30_minutes_dt, get_start_datetime

logger = structlog.stdlib.get_logger()

# Blend model weights for different forecast horizons
# merged from: cnn, pvnet_v2, National_xg
FORECAST_BLEND_WEIGHTS = [
    {
        # cnn
        "end_horizon_hour": 1,
        "end_weight": [1, 0, 0],
    },
    {
        # cnn to pvnet_v2
        "start_horizon_hour": 1,
        "end_horizon_hour": 2,
        "start_weight": [1, 0, 0],
        "end_weight": [0, 0, 1],
    },
    {
        # pvnet_v2
        "start_horizon_hour": 2,
        "end_horizon_hour": 7,
        "start_weight": [0, 0, 1],
        "end_weight": [0, 0, 1],
    },
    {
        # pvnet_v2 to National_xg
        "start_horizon_hour": 7,
        "end_horizon_hour": 8,
        "start_weight": [0, 0, 1],
        "end_weight": [0, 1, 0],
    },
    {
        # National_xg
        "start_horizon_hour": 8,
        "end_horizon_hour": 9,
        "start_weight": [0, 1, 0],
        "end_weight": [0, 1, 0],
    },
]


class BaseDBConnection(abc.ABC):
    """A base class for database connections with a static method to get a connection.

    Methods
    -------
    get_connection() : static method
        Gets the database connection. If a valid PostgreSQL database URL is set in
        the "DB_URL" environment variable, returns a DatabaseConnection instance.
        Otherwise, returns a DummyDBConnection instance.
    """

    @staticmethod
    def get_connection() -> Union["DatabaseConnection", "DummyDBConnection"]:
        """
        Get the appropriate database connection based on environment configuration.

        Returns
        -------
        Union[DatabaseConnection, DummyDBConnection]
            The database connection instance
        """
        db_url = os.getenv("DB_URL")
        if db_url and db_url.find("postgresql") != -1:
            return DatabaseConnection(url=db_url, echo=False)
        else:
            return DummyDBConnection()


class DummyDBConnection(BaseDBConnection):
    """A placeholder database connection for testing/development environments.

    This serves as a mock when a valid PostgreSQL database connection is not available.
    A better example can be found in the [india-api](
    https://github.com/openclimatefix/india-api/blob/f4e3b776194290d78e1c9702b792cbb88edf4b90/src/india_api/cmd/main.py#L12
    ) repository.

    Methods
    ----------
    get_session():
        Returns None for now, but should mock the session if possible,
        if we keep the current DB/datamodel implementation.
    """

    def __init__(self) -> None:
        """Initialize the DummyDBConnection."""
        pass

    def get_session(self) -> None:
        """
        Return None for now, but should mock the session if needed in the future.

        Returns
        -------
        None
        """
        return None


def get_db_connection() -> BaseDBConnection:
    """
    Return either the datamodel connection or a dummy connection.

    Returns
    -------
    BaseDBConnection
        A database connection instance
    """
    return BaseDBConnection.get_connection()


# Initialize database connection
db_conn = get_db_connection()


def get_session() -> Session:
    """
    Get database session as a FastAPI dependency.

    Yields
    ------
    Session
        A database session
    """
    with db_conn.get_session() as session:
        yield session


# Status functions
def get_latest_status_from_database(session: Session) -> Status:
    """
    Get latest status from database.

    Parameters
    ----------
    session : Session
        SQLAlchemy session

    Returns
    -------
    Status
        Latest status from database
    """
    latest_status = get_latest_status(session)
    return Status.from_orm(latest_status)


# Forecast functions
def get_forecasts_from_database(
    session: Session,
    historic: Optional[bool] = False,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    compact: Optional[bool] = False,
    gsp_ids: Optional[List[str]] = None,
    creation_utc_limit: Optional[datetime] = None,
) -> Union[ManyForecasts, List[OneDatetimeManyForecastValues]]:
    """
    Get forecasts from database for all GSPs.

    Parameters
    ----------
    session : Session
        SQLAlchemy session
    historic : bool, optional
        Whether to get historic forecasts, by default False
    start_datetime_utc : datetime, optional
        Start datetime for forecast retrieval, by default None
    end_datetime_utc : datetime, optional
        End datetime for forecast retrieval, by default None
    compact : bool, optional
        Whether to return compact format, by default False
    gsp_ids : List[str], optional
        List of GSP IDs to filter by, by default None
    creation_utc_limit : datetime, optional
        Limit forecasts by creation date, by default None

    Returns
    -------
    Union[ManyForecasts, List[OneDatetimeManyForecastValues]]
        Forecasts in requested format

    Raises
    ------
    HTTPException
        If creation_utc_limit is provided with historic=True
    """
    if historic:
        if creation_utc_limit is not None:
            raise HTTPException(
                status_code=400,
                detail="creation_utc_limit is not supported for historic=True forecasts. "
                "These forecast are continuously updated, "
                "compare to a forecast made a particular time.",
            )

        start_datetime = get_start_datetime(start_datetime=start_datetime_utc)

        forecasts = get_all_gsp_ids_latest_forecast(
            session=session,
            start_target_time=start_datetime,
            preload_children=True,
            historic=True,
            include_national=False,
            model_name="blend",
            end_target_time=end_datetime_utc,
            gsp_ids=gsp_ids,
        )

        logger.debug(f"Found {len(forecasts)} forecasts from database")

    else:
        # Speed up read time by only looking at last 12 hours of results with floor 30 mins
        if start_datetime_utc is None:
            start_datetime_utc = floor_30_minutes_dt(
                datetime.now(tz=timezone.utc) - timedelta(hours=12)
            )
        if creation_utc_limit is None:
            start_created_utc = floor_30_minutes_dt(
                datetime.now(tz=timezone.utc) - timedelta(hours=12)
            )
        else:
            start_created_utc = creation_utc_limit - timedelta(hours=12)

        forecasts = get_all_gsp_ids_latest_forecast(
            session=session,
            start_created_utc=start_created_utc,
            start_target_time=start_datetime_utc,
            preload_children=True,
            model_name="blend",
            end_target_time=end_datetime_utc,
            end_created_utc=creation_utc_limit,
            gsp_ids=gsp_ids,
        )

    if compact:
        return convert_forecasts_to_many_datetime_many_generation(
            forecasts=forecasts,
            historic=historic,
            start_datetime_utc=start_datetime_utc,
            end_datetime_utc=end_datetime_utc,
        )
    else:
        # Convert to pydantic objects
        if historic:
            forecasts = [Forecast.from_orm_latest(forecast) for forecast in forecasts]
        else:
            forecasts = [Forecast.from_orm(forecast) for forecast in forecasts]

        forecasts = filter_forecast_values(
            end_datetime_utc=end_datetime_utc,
            forecasts=forecasts,
            start_datetime_utc=start_datetime_utc,
        )

        return ManyForecasts(forecasts=forecasts)


def get_forecasts_for_a_specific_gsp_from_database(
    session: Session, gsp_id: int, historic: Optional[bool] = False
) -> Forecast:
    """
    Get forecasts for one GSP from database.

    Parameters
    ----------
    session : Session
        SQLAlchemy session
    gsp_id : int
        GSP ID to get forecasts for
    historic : bool, optional
        Whether to get historic forecasts, by default False

    Returns
    -------
    Forecast
        Latest forecast for the specified GSP
    """
    start_datetime = get_start_datetime()

    forecast = get_latest_forecast(
        session=session,
        gsp_id=gsp_id,
        historic=historic,
        start_target_time=start_datetime,
    )

    logger.debug("Found latest forecasts")

    if historic:
        return Forecast.from_orm_latest(forecast)
    else:
        return Forecast.from_orm(forecast)


def get_latest_forecast_values_for_a_specific_gsp_from_database(
    session: Session,
    gsp_id: int,
    forecast_horizon_minutes: Optional[int] = None,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    creation_utc_limit: Optional[datetime] = None,
) -> List[ForecastValue]:
    """
    Get the forecast values for yesterday and today for one GSP.

    Parameters
    ----------
    session : Session
        SQLAlchemy session
    gsp_id : int
        GSP ID, 0 is national
    forecast_horizon_minutes : int, optional
        Forecast horizon in minutes (e.g., 35 minutes means get the latest forecast
        made 35 minutes before the target time)
    start_datetime_utc : datetime, optional
        Start datetime for the query, by default None
    end_datetime_utc : datetime, optional
        End datetime for the query, by default None
    creation_utc_limit : datetime, optional
        Limit forecasts by creation date, by default None

    Returns
    -------
    List[ForecastValue]
        List of latest forecast values
    """
    start_datetime = get_start_datetime(start_datetime=start_datetime_utc, days=365)

    if (forecast_horizon_minutes is None) and (creation_utc_limit is None):
        forecast_values = get_forecast_values_latest(
            session=session,
            gsp_id=gsp_id,
            start_datetime=start_datetime,
            model_name="blend",
            end_datetime=end_datetime_utc,
        )
    else:
        # Determine which model to use based on date ranges
        if creation_utc_limit is not None and creation_utc_limit < datetime.now(
            tz=timezone.utc
        ) - timedelta(days=7):
            model: Type[Union[ForecastValueSQL, ForecastValueSevenDaysSQL]] = ForecastValueSQL
        elif start_datetime_utc is not None and start_datetime_utc < datetime.now(
            tz=timezone.utc
        ) - timedelta(days=7):
            model = ForecastValueSQL
        else:
            model = ForecastValueSevenDaysSQL

        # For future N hr forecasts, make sure to show forecasts made N hours ago
        if creation_utc_limit is None and forecast_horizon_minutes is not None:
            creation_utc_limit = datetime.now(tz=timezone.utc) - timedelta(
                minutes=forecast_horizon_minutes
            )

        forecast_values = get_forecast_values(
            session=session,
            gsp_id=gsp_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime_utc,
            forecast_horizon_minutes=forecast_horizon_minutes,
            model_name="blend",
            model=model,
            only_return_latest=True,
            created_utc_limit=creation_utc_limit,
        )

    if len(forecast_values) == 0:
        return []

    # Convert to pydantic objects
    if (
        isinstance(forecast_values[0], ForecastValueSevenDaysSQL)
        or isinstance(forecast_values[0], ForecastValueSQL)
        or isinstance(forecast_values[0], ForecastValueLatestSQL)
    ):
        forecast_values = [ForecastValue.from_orm(f) for f in forecast_values]

    return forecast_values


def get_latest_national_forecast_from_database(session: Session) -> Forecast:
    """
    Get the national level forecast from the database.

    Parameters
    ----------
    session : Session
        SQLAlchemy session

    Returns
    -------
    Forecast
        Latest national forecast
    """
    logger.debug("Getting latest national forecast")
    forecast = get_latest_national_forecast(session=session)
    logger.debug(forecast)
    return Forecast.from_orm(forecast)


# GSP Yield / Truth Value functions
def get_truth_values_for_a_specific_gsp_from_database(
    session: Session,
    gsp_id: int,
    regime: str = "in-day",
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
) -> List[GSPYield]:
    """
    Get the truth value for one GSP for yesterday and today.

    Parameters
    ----------
    session : Session
        SQLAlchemy session
    gsp_id : int
        GSP ID
    regime : str, optional
        Option for "in-day" or "day-after", by default "in-day"
    start_datetime : datetime, optional
        Start datetime for the query. If not set, after now, or set to over three days ago,
        defaults to N_HISTORY_DAYS env var (usually yesterday)
    end_datetime : datetime, optional
        End datetime for the query, by default None

    Returns
    -------
    List[GSPYield]
        List of GSP yields
    """
    stmt = (
        select(GSPYieldSQL)
        .join(LocationSQL, GSPYieldSQL.location_id == LocationSQL.id)
        .where(LocationSQL.gsp_id == gsp_id)
    )
    if start_datetime is not None:
        stmt = stmt.where(GSPYieldSQL.datetime_utc >= start_datetime)
    if end_datetime is not None:
        stmt = stmt.where(GSPYieldSQL.datetime_utc <= end_datetime)

    result = session.execute(stmt.order_by(GSPYieldSQL.datetime_utc))
    rows = cast(List[GSPYieldSQL], result.scalars().all())
    return [GSPYield.from_orm(r) for r in rows]


def get_truth_values_for_all_gsps_from_database(
    session: Session,
    regime: str = "in-day",
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    compact: bool = False,
    gsp_ids: Optional[List[int]] = None,
) -> Union[List[LocationWithGSPYields], List[GSPYieldGroupByDatetime]]:
    """
    Get the truth value for all GSPs for yesterday and today.

    Parameters
    ----------
    session : Session
        SQLAlchemy session
    regime : str, optional
        Option for "in-day" or "day-after", by default "in-day"
    start_datetime_utc : datetime, optional
        Start datetime for the query. If not set, after now, or set to over three days ago,
        defaults to N_HISTORY_DAYS env var (usually yesterday)
    end_datetime_utc : datetime, optional
        End datetime for the query, by default None
    compact : bool, optional
        If True, return a list of GSPYieldGroupByDatetime objects, by default False
    gsp_ids : List[int], optional
        Optional list of GSP IDs to load, by default None

    Returns
    -------
    Union[List[LocationWithGSPYields], List[GSPYieldGroupByDatetime]]
        Truth values in requested format
    """
    start_datetime = get_start_datetime(start_datetime=start_datetime_utc)

    if gsp_ids is None:
        gsp_ids = list(range(1, N_GSP + 1))

    locations = get_gsp_yield_by_location(
        session=session,
        gsp_ids=gsp_ids,
        start_datetime_utc=start_datetime,
        end_datetime_utc=end_datetime_utc,
        regime=regime,
    )

    if compact:
        return convert_location_sql_to_many_datetime_many_generation(locations)
    else:
        return [LocationWithGSPYields.from_orm(location) for location in locations]


# Location/System functions
def get_gsp_system(session: Session, gsp_id: Optional[int] = None) -> List[Location]:
    """
    Get GSP system details.

    Parameters
    ----------
    session : Session
        SQLAlchemy session
    gsp_id : int, optional
        GSP ID. If None, get all systems, by default None

    Returns
    -------
    List[Location]
        List of GSP system locations
    """
    if gsp_id is not None:
        # Adjust label for national location
        if gsp_id == 0:
            label = national_gb_label
        else:
            label = None

        # Get one system
        gsp_systems = [get_location(session=session, gsp_id=gsp_id, label=label)]
    else:
        gsp_systems = get_all_locations(session=session)

    # Convert to pydantic objects
    return [Location.from_orm(gsp_system) for gsp_system in gsp_systems]


# API request tracking
def save_api_call_to_db(request: Request, session: Session, user: Optional[User] = None) -> None:
    """
    Save API call to database.

    If the user does not have an email address, we save the email as unknown.

    Parameters
    ----------
    request : Request
        The API request object
    session : Session
        The database session
    user : User, optional
        The user object, by default None
    """
    url = str(request.url)

    if user is None:
        email = "unknown"
    else:
        email = user.email

    # Get user from db
    db_user = get_user_from_db(session=session, email=email)

    # Create and save API request
    logger.info(f"Saving api call ({url=}) to database for user {email}")
    api_request = APIRequestSQL(url=url, user=db_user)

    session.add(api_request)
    session.commit()
