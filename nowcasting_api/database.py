""" Functions to read from the database and format """

import abc
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union

import structlog
from fastapi.exceptions import HTTPException
from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.models import (APIRequestSQL, Forecast,
                                         ForecastValue, ForecastValueLatestSQL,
                                         ForecastValueSevenDaysSQL,
                                         ForecastValueSQL, Location,
                                         ManyForecasts, Status)
from nowcasting_datamodel.read.read import (get_all_gsp_ids_latest_forecast,
                                            get_all_locations,
                                            get_forecast_values,
                                            get_forecast_values_latest,
                                            get_latest_forecast,
                                            get_latest_national_forecast,
                                            get_latest_status, get_location,
                                            national_gb_label)
from nowcasting_datamodel.read.read_gsp import (get_gsp_yield,
                                                get_gsp_yield_by_location)
from nowcasting_datamodel.read.read_user import get_user as get_user_from_db
from nowcasting_datamodel.save.update import N_GSP
from pydantic_models import (
    GSPYield, GSPYieldGroupByDatetime, LocationWithGSPYields,
    OneDatetimeManyForecastValues,
    convert_forecasts_to_many_datetime_many_generation,
    convert_location_sql_to_many_datetime_many_generation)
from sqlalchemy.orm.session import Session
from utils import (filter_forecast_values, floor_30_minutes_dt,
                   get_start_datetime)


class BaseDBConnection(abc.ABC):
    """This is a base class for database connections with one static method get_connection().

    Methods
    -------
    get_connection : static method
        It gets the database connection. If a valid Postgresql database URL is set in
        the "DB_URL" environment variable, get_connection returns an instance
        of DatabaseConnection(). If not, it returns an instance of the DummyDBConnection.
    """

    @staticmethod
    def get_connection():
        """
        Get the database connection.
        """
        db_url = os.getenv("DB_URL")
        if db_url and db_url.find("postgresql") != -1:
            return DatabaseConnection(url=db_url, echo=False)
        else:
            return DummyDBConnection()


class DummyDBConnection(BaseDBConnection):
    """The DummyDBConnection serves as a placeholder database connection

    This might be useful when a valid Postgresql
    database connection is not available. in testing or development environments.
    Feel free to improve on this implementation and submit a pull request!
    A better example can be found in the [india-api](
    https://github.com/openclimatefix/india-api/blob/f4e3b776194290d78e1c9702b792cbb88edf4b90/src/india_api/cmd/main.py#L12
    ) repository.

    It inherits from the BaseDBConnection class and implements the methods accordingly.

    Methods
    ----------
    get_session:
        Returns None for now, but should mock the session if possible,
        if we keep the current DB/datamodel implementation.
    """

    def __init__(self):
        """Initializes the DummyDBConnection"""
        pass

    def get_session(self):
        """Returns None for now, but mock the session if we keep the current implementation."""
        return None


def get_db_connection() -> BaseDBConnection:
    """Return either the datamodel connection or a dummy connection"""
    return BaseDBConnection.get_connection()


db_conn = get_db_connection()

logger = structlog.stdlib.get_logger()

# merged from
# - cnn
# - pvnet_v2
# - National_xg
weights = [
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


def get_latest_status_from_database(session: Session) -> Status:
    """Get latest status from database"""
    latest_status = get_latest_status(session)

    # convert to PyDantic object
    latest_status = Status.from_orm(latest_status)

    return latest_status


def get_forecasts_from_database(
    session: Session,
    historic: Optional[bool] = False,
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    compact: Optional[bool] = False,
    gsp_ids: Optional[List[str]] = None,
    creation_utc_limit: Optional[datetime] = None,
) -> Union[ManyForecasts, List[OneDatetimeManyForecastValues]]:
    """Get forecasts from database for all GSPs"""
    # get the latest forecast for all gsps.

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
        # To speed up read time we only look at the last 12 hours of results, and take floor 30 mins
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
        # change to pydantic objects
        if historic:
            forecasts = [Forecast.from_orm_latest(forecast) for forecast in forecasts]
        else:
            forecasts = [Forecast.from_orm(forecast) for forecast in forecasts]

        forecasts = filter_forecast_values(
            end_datetime_utc=end_datetime_utc,
            forecasts=forecasts,
            start_datetime_utc=start_datetime_utc,
        )

        # return as many forecasts
        return ManyForecasts(forecasts=forecasts)


def get_forecasts_for_a_specific_gsp_from_database(
    session: Session, gsp_id, historic: Optional[bool] = False
) -> Forecast:
    """Get forecasts for one GSP from database"""

    start_datetime = get_start_datetime()

    # get forecast from database
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
    """Get the forecast values for yesterday and today for one gsp

    :param session: sqlalchemy session
    :param gsp_id: gsp id, 0 is national
    :param forecast_horizon_minutes: Optional forecast horizon in minutes. I.e 35 minutes, means
        get the latest forecast made 35 minutes before the target time.
    :return: list of latest forecat values
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
        if creation_utc_limit is not None and creation_utc_limit < datetime.now(
            tz=timezone.utc
        ) - timedelta(days=7):
            model = ForecastValueSQL
        elif start_datetime_utc is not None and start_datetime_utc < datetime.now(
            tz=timezone.utc
        ) - timedelta(days=7):
            model = ForecastValueSQL
        else:
            model = ForecastValueSevenDaysSQL

        # to make sure future N hr forecasts show a forecast that was made N hours ago
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

    # convert to pydantic objects
    if (
        isinstance(forecast_values[0], ForecastValueSevenDaysSQL)
        or isinstance(forecast_values[0], ForecastValueSQL)
        or isinstance(forecast_values[0], ForecastValueLatestSQL)
    ):
        forecast_values = [ForecastValue.from_orm(f) for f in forecast_values]

    return forecast_values


def get_session():
    """Get database settion"""

    with db_conn.get_session() as s:
        yield s


def get_latest_national_forecast_from_database(session: Session) -> Forecast:
    """Get the national level forecast from the database"""

    logger.debug("Getting latest national forecast")

    forecast = get_latest_national_forecast(session=session)
    logger.debug(forecast)
    return Forecast.from_orm(forecast)


def get_truth_values_for_a_specific_gsp_from_database(
    session: Session,
    gsp_id: int,
    regime: Optional[str] = "in-day",
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
) -> List[GSPYield]:
    """Get the truth value for one gsp for yesterday and today

    :param session: sql session
    :param gsp_id: gsp id
    :param regime: option for "in-day" or "day-after"
    :param start_datetime: optional start datetime for the query.
     If not set, after now, or set to over three days ago
     defaults to N_HISTORY_DAYS env var, which defaults to yesterday.
    :param end_datetime: optional end datetime for the query.
    :return: list of gsp yields
    """

    start_datetime = get_start_datetime(start_datetime=start_datetime)

    return get_gsp_yield(
        session=session,
        gsp_ids=[gsp_id],
        start_datetime_utc=start_datetime,
        end_datetime_utc=end_datetime,
        regime=regime,
    )


def get_truth_values_for_all_gsps_from_database(
    session: Session,
    regime: Optional[str] = "in-day",
    start_datetime_utc: Optional[datetime] = None,
    end_datetime_utc: Optional[datetime] = None,
    compact: Optional[bool] = False,
    gsp_ids: Optional[List[int]] = None,
) -> Union[List[LocationWithGSPYields], List[GSPYieldGroupByDatetime]]:
    """Get the truth value for all gsps for yesterday and today

    :param session: sql session
    :param regime: option for "in-day" or "day-after"
    :param start_datetime_utc: optional start datetime for the query.
     If not set, after now, or set to over three days ago
     defaults to N_HISTORY_DAYS env var, which defaults to yesterday.
    :param end_datetime_utc: optional end datetime for the query.
    :param compact: if True, return a list of GSPYieldGroupByDatetime objects
    :param gsp_ids: optional list of gsp ids to load
    :return: list of gsp yields
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


def get_gsp_system(session: Session, gsp_id: Optional[int] = None) -> List[Location]:
    """Get gsp system details

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


def save_api_call_to_db(request, session, user=None):
    """
    Save API call to database

    If the user does not have an email address, we will save the email as unknown

    :param request: The API request object
    :param session: The database session
    :param user: The user object (optional)
    :return: None
    """

    url = str(request.url)

    if user is None:
        email = "unknown"
    else:
        email = user.email

    # get user from db
    user = get_user_from_db(session=session, email=email)
    # make api call
    logger.info(f"Saving api call ({url=}) to database for user {email}")
    api_request = APIRequestSQL(url=url, user=user)

    # commit to database
    session.add(api_request)
    session.commit()
