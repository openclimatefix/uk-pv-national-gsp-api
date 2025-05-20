""" Get data from database - optimized"""

from datetime import datetime, timedelta, timezone

from nowcasting_datamodel.models import ForecastSQL, ForecastValueLatestSQL, ForecastValueSevenDaysSQL, LocationSQL, MLModelSQL
from pydantic_models import NationalForecastValue, OneDatetimeManyForecastValues
from sqlalchemy.orm.session import Session
from sqlalchemy import text
from sqlalchemy import select

from utils import (
    get_start_datetime,
)
import structlog

logger = structlog.stdlib.get_logger()


def get_forecast_values_all_compact(
    session: Session,
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    gsp_ids=None,
) -> [OneDatetimeManyForecastValues]:
    """Get forecast values from the database.

    We get all the latest forecast values for the blend model.
    We convert the sqlalchemy objects to OneDatetimeManyForecastValues
    Particular focus has been put on only get the data we need from the database.

    This function
    1. get model ids
    2. get forecast values from the forecast_value_latest table.
        We tried to only get the relevant data as needed, as this is normally a larger query
    3. converts to a dict of {datetime: {gsp_id: forecast_value}}
    4. converts to a list of OneDatetimeManyForecastValues objects
    """
    # 1. get model ids
    model_ids = session.query(MLModelSQL.id).filter(MLModelSQL.name == "blend").all()
    model_ids = [model_id[0] for model_id in model_ids]

    # 2. get forecast values from database
    query = session.query(
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.expected_power_generation_megawatts,
        ForecastValueLatestSQL.gsp_id,
    )

    # distinct on target_time
    query = query.distinct(ForecastValueLatestSQL.gsp_id, ForecastValueLatestSQL.target_time)

    # join with model table
    query = query.filter(ForecastValueLatestSQL.model_id.in_(model_ids))

    if start_datetime_utc is not None:
        query = query.filter(ForecastValueLatestSQL.target_time >= start_datetime_utc)
    if end_datetime_utc is not None:
        query = query.filter(ForecastValueLatestSQL.target_time <= end_datetime_utc)

    if gsp_ids is not None:
        query = query.filter(ForecastValueLatestSQL.gsp_id.in_(gsp_ids))
    else:
        # dont get gps id 0
        query = query.filter(ForecastValueLatestSQL.gsp_id != 0)

    # order by target time and created utc desc
    query = query.order_by(
        ForecastValueLatestSQL.gsp_id,
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.created_utc.desc(),
    )

    forecast_values = query.all()

    # 3. convert to OneDatetimeManyForecastValues
    many_forecast_values_by_datetime = {}

    # loop over locations and gsp yields to create a dictionary of gsp generation by datetime
    for forecast_value in forecast_values:
        datetime_utc = forecast_value[0]
        power_kw = forecast_value[1]
        gsp_id = forecast_value[2]

        power_kw = round(power_kw, 2)

        # if the datetime object is not in the dictionary, add it
        if datetime_utc not in many_forecast_values_by_datetime:
            many_forecast_values_by_datetime[datetime_utc] = {gsp_id: power_kw}
        else:
            many_forecast_values_by_datetime[datetime_utc][gsp_id] = power_kw

    # 4. convert dictionary to list of OneDatetimeManyForecastValues objects
    many_forecast_values = []
    for datetime_utc, forecast_values in many_forecast_values_by_datetime.items():
        many_forecast_values.append(
            OneDatetimeManyForecastValues(
                datetime_utc=datetime_utc, forecast_values=forecast_values
            )
        )

    return many_forecast_values


def get_national_forecast_values(session,
            forecast_horizon_minutes,
            start_datetime_utc,
            end_datetime_utc,
            creation_utc_limit,
            model_name,
            trend_adjuster_on,
            get_plevels) -> [NationalForecastValue]:



    if forecast_horizon_minutes is not None:
        model = ForecastValueSevenDaysSQL

        start_datetime_utc = get_start_datetime(start_datetime=start_datetime_utc, days=365)
        import time
        # 1. get model ids
        # import time
        # t = time.time()
        # model_ids = session.query(MLModelSQL.id).filter(MLModelSQL.name == model_name).all()
        # model_ids = [model_id[0] for model_id in model_ids]
        # print("model_ids", time.time() - t, "seconds")

        # get forecast_ids
        # query = session.query(ForecastSQL.id)
        # query = query.filter(ForecastSQL.historic == False)
        # query = query.join(LocationSQL)
        # query = query.join(MLModelSQL)
        # # query = query.filter(ForecastSQL.model_id.in_(model_ids))
        # query = query.filter(LocationSQL.gsp_id == 0)
        # query = query.filter(MLModelSQL.name == model_name)
        # query = query.filter(ForecastSQL.created_utc >= start_datetime_utc - timedelta(days=2))
        #
        #
        # t =time.time()
        # forecast_ids = query.all()
        # forecast_ids = [forecast_id[0] for forecast_id in forecast_ids]
        # print("forecast_ids", time.time() - t, "seconds", len(forecast_ids))


        logger.debug(f"Got forecast ids")

        values = [model.target_time,
                  model.expected_power_generation_megawatts,
                  model.properties,
                  model.adjust_mw]

        if get_plevels:
            pass

        if trend_adjuster_on:
            pass



        if creation_utc_limit is None:
            creation_utc_limit = datetime.now(tz=timezone.utc) - timedelta(
                minutes=forecast_horizon_minutes
            )

        creation_utc_lower_bound = start_datetime_utc - timedelta(
                minutes=forecast_horizon_minutes
            ) - timedelta(days=2)


        query = session.query(*values)

        query = query.join(ForecastSQL)
        query = query.filter(ForecastSQL.historic == False)
        query = query.join(LocationSQL)
        query = query.join(MLModelSQL)
        # query = query.filter(ForecastSQL.model_id.in_(model_ids))
        query = query.filter(LocationSQL.gsp_id == 0)
        query = query.filter(MLModelSQL.name == model_name)
        query = query.filter(ForecastSQL.created_utc >= start_datetime_utc - timedelta(days=2))

        query = query.distinct(model.target_time)
        # query = query.filter(model.forecast_id.in_(forecast_ids))
        query = query.filter(model.target_time >= start_datetime_utc)

        # filter for forecast_horizon_minutes
        if forecast_horizon_minutes is not None:
            query = query.filter(
                model.target_time - model.created_utc
                >= text(f"interval '{forecast_horizon_minutes} minute'")
            )

            query = query.filter(
                model.created_utc - datetime.now(tz=timezone.utc)
                <= text(f"interval '{forecast_horizon_minutes} minute'")
            )

        if end_datetime_utc is not None:
            query = query.filter(ForecastValueSevenDaysSQL.target_time <= end_datetime_utc)

        query = query.filter(ForecastSQL.created_utc >= creation_utc_lower_bound)
        query = query.filter(model.created_utc >= creation_utc_lower_bound)
        query = query.filter(model.created_utc <= creation_utc_limit)

        query = query.order_by(ForecastValueSevenDaysSQL.target_time,
                               ForecastValueSevenDaysSQL.created_utc.desc())
        # query = query.limit(200)

        t = time.time()
        forecast_values = query.all()
        print("forecast_values", time.time()-t, "seconds", len(forecast_values))

        # import pandas as pd
        # forecast_values = pd.read_sql_query(
        #     query, session.bind, index_col="target_time", parse_dates=["target_time"]
        # )
        # print("forecast_values", time.time() - t, "seconds")

        t = time.time()
        forecast_values = [
            NationalForecastValue(
                target_time=forecast_value[0],
                expected_power_generation_megawatts=forecast_value[1],
            )
            for forecast_value in forecast_values
        ]
        print("format", time.time() - t, "seconds", len(forecast_values))

        return forecast_values






