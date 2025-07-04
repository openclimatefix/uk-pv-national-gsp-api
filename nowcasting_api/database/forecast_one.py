"""Get data from database - optimized"""

import os
from datetime import datetime, timezone, timedelta

from nowcasting_datamodel.models import (
    Forecast,
    ForecastSQL,
    ForecastValue,
    ForecastValueSQL,
    ForecastValueLatestSQL,
    ForecastValueSevenDaysSQL,
    InputDataLastUpdated,
    InputDataLastUpdatedSQL,
    Location,
    LocationSQL,
    ManyForecasts,
    MLModel,
    MLModelSQL,
)
from pydantic_models import OneDatetimeManyForecastValues, NationalForecastValue
from sqlalchemy import NUMERIC
from sqlalchemy.orm import Query
from sqlalchemy.orm.session import Session

adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))


def get_national_forecast_values(session: Session,
                                       start_datetime_utc: datetime | None = None,
                                       end_datetime_utc: datetime | None = None,
                                       creation_limit_utc: str | None = None,
                                       forecast_horizon_minutes: int | None = None,
                                       trend_adjuster_on: bool | None = True,
                                       model_name: str = "blend") -> list[ForecastValue]:
    raw_fv = get_raw_forecast_values_for_one_gsp_id(
        session=session,
        start_datetime_utc=start_datetime_utc,
        end_datetime_utc=end_datetime_utc,
        creation_limit_utc=creation_limit_utc,
        gsp_id=0,
        forecast_horizon_minutes=forecast_horizon_minutes,
        trend_adjuster_on=trend_adjuster_on,
        model_name=model_name
    )

    fvs = []
    for target_time, expected_power_generation_megawatts in raw_fv:
        fv = NationalForecastValue(target_time=target_time,
                           expected_power_generation_megawatts=expected_power_generation_megawatts)
        # TODO add probablistic

        # TODO add normalized values

        # TODO add adjuster
        fvs.append(fv)

    return fvs

def get_forecast_values_for_one_gsp_id(session: Session,
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    creation_limit_utc: str | None = None,
    gsp_id: int | None = None,
    forecast_horizon_minutes: int | None = None,
    trend_adjuster_on: bool | None = True,
    model_name: str = "blend") -> list[ForecastValue]:

    raw_fv = get_raw_forecast_values_for_one_gsp_id(
        session=session,
        start_datetime_utc=start_datetime_utc,
        end_datetime_utc=end_datetime_utc,
        creation_limit_utc=creation_limit_utc,
        gsp_id=gsp_id,
        forecast_horizon_minutes=forecast_horizon_minutes,
        trend_adjuster_on=trend_adjuster_on,
        model_name=model_name
    )

    fvs = []
    for target_time, expected_power_generation_megawatts in raw_fv:
        fv = ForecastValue(target_time=target_time,
                      expected_power_generation_megawatts=expected_power_generation_megawatts)
        fvs.append(fv)

    return fvs



def get_raw_forecast_values_for_one_gsp_id(
    session: Session,
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    creation_limit_utc: str | None = None,
    gsp_id: int | None = None,
    forecast_horizon_minutes: int | None = None,
    trend_adjuster_on: bool | None = True,
    model_name: str = "blend",
) -> []:
    """Get forecast values from the database for one gsp_id.

    We get all the latest forecast values for the blend model.
    We convert the sqlalchemy objects to OneDatetimeManyForecastValues
    Particular focus has been put on only get the data we need from the database.

    This function
    1. get model ids
    2. get forecast values from the forecast_value_latest table.
        We tried to only get the relevant data as needed, as this is normally a larger query
    3. converts to a dict of {datetime: {gsp_id: forecast_value}}
    4. converts to a list of OneDatetimeManyForecastValues objects

    Returns a [] forecast values objects, each object is
     - target_time
     - expected_power_generation_megawatts
    """

    # 1. Choose which model table to use
    now_minus_seven_days = datetime.now(tz=timezone.utc) - timedelta(days=7)
    # TODO do we need to add something about start and end datetimes too
    if forecast_horizon_minutes is None and creation_limit_utc is None:
        fv_model = ForecastValueLatestSQL
    elif creation_limit_utc is not None and creation_limit_utc < now_minus_seven_days:
        fv_model = ForecastValueSQL
    elif start_datetime_utc is not None and start_datetime_utc < now_minus_seven_days:
        fv_model = ForecastValueSQL
    else:
        fv_model = ForecastValueSevenDaysSQL


    # 1. get model ids
    model_ids = session.query(MLModelSQL.id).filter(MLModelSQL.name == model_name).all()
    model_ids = [model_id[0] for model_id in model_ids]

    # 2. get forecast values from database
    query = session.query(
        fv_model.target_time,
        fv_model.expected_power_generation_megawatts.cast(NUMERIC(10, 2)),
    )

    # distinct on target_time
    query = query.distinct(fv_model.target_time)

    # join with model table
    if fv_model == ForecastValueLatestSQL:
        query = query.filter(fv_model.model_id.in_(model_ids))
    else:
        query = query.join(ForecastSQL)
        query = query.filter(ForecastSQL.model_id.in_(model_ids))

    # filters
    query = filter_start_and_end_datetime(
        query=query, start_datetime_utc=start_datetime_utc, end_datetime_utc=end_datetime_utc
    )
    # if latest
    if fv_model == ForecastValueLatestSQL:
        query = query.filter(fv_model.gsp_id == gsp_id)
    else:
        # filter by gsp_id
        query = query.join(LocationSQL)
        query = query.filter(LocationSQL.gsp_id == gsp_id)

    # order by target time and created utc desc
    query = query.order_by(
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.created_utc.desc(),
    )

    forecast_values = query.all()

    return forecast_values



def filter_start_and_end_datetime(
    query: Query,
    end_datetime_utc: datetime | None,
    start_datetime_utc: datetime | None,
    model=ForecastValueLatestSQL,
):
    """Filter by start and end datetime."""
    if start_datetime_utc is not None:
        query = query.filter(model.target_time >= start_datetime_utc)
    if end_datetime_utc is not None:
        query = query.filter(model.target_time <= end_datetime_utc)
    return query


# TODO get forecast obeject too