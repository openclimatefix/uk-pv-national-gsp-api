""" Get data from database - optimized"""

from datetime import datetime, timedelta, timezone

from nowcasting_datamodel.models import ForecastSQL, ForecastValueLatestSQL, ForecastValueSQL, ForecastValueSevenDaysSQL, LocationSQL, MLModelSQL
from pydantic_models import NationalForecastValue, OneDatetimeManyForecastValues
from sqlalchemy.orm.session import Session
from sqlalchemy import text
from sqlalchemy import select
from utils import (
    N_CALLS_PER_HOUR,
    filter_forecast_values,
    format_datetime,
    format_plevels,
    limiter,
    remove_duplicate_values,
)

import os
from datetime import datetime

from nowcasting_datamodel.models import (
    Forecast,
    ForecastSQL,
    ForecastValue,
    ForecastValueLatestSQL,
    InputDataLastUpdated,
    InputDataLastUpdatedSQL,
    Location,
    LocationSQL,
    ManyForecasts,
    MLModel,
    MLModelSQL,
)
from pydantic_models import OneDatetimeManyForecastValues
from sqlalchemy import NUMERIC
from sqlalchemy.orm import Query
from sqlalchemy.orm.session import Session

adjust_limit = float(os.getenv("ADJUST_MW_LIMIT", 0.0))

from utils import (
    get_start_datetime,
)
import structlog

logger = structlog.stdlib.get_logger()


def get_national_forecast_values(session,
            forecast_horizon_minutes,
            start_datetime_utc,
            end_datetime_utc,
            creation_utc_limit,
            model_name,
            trend_adjuster_on,
            get_plevels) -> [NationalForecastValue]:



    # if forecast_horizon_minutes or creation_utc_limit is not None,
    # then we are not going to load from the lastest values
    # Therefore we have to look at ForecastValueSevenDaysSQL or ForecastValue
    if (forecast_horizon_minutes is not None) or (creation_utc_limit is not None):

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

        start_datetime_utc = get_start_datetime(start_datetime=start_datetime_utc, days=365)
        import time

        logger.debug(f"Got forecast ids")

        values = [model.target_time,
                  model.expected_power_generation_megawatts,
                  model.properties,
                  model.adjust_mw]

        if get_plevels:
            pass

        if trend_adjuster_on:
            pass

        # create the creation utc upper bound
        if creation_utc_limit is None:
            creation_utc_limit = datetime.now(tz=timezone.utc)
        if forecast_horizon_minutes is not None:
            creation_utc_limit -= timedelta(
                minutes=forecast_horizon_minutes
            )

        # create the creation utc lower bound
        creation_utc_lower_bound = start_datetime_utc - timedelta(days=2)
        if forecast_horizon_minutes is not None:
            creation_utc_lower_bound -= timedelta(
                minutes=forecast_horizon_minutes
            )

        # start query
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
                model.horizon_minutes >= forecast_horizon_minutes
            )

            # TODO do we need this?
            # query = query.filter(
            #     model.created_utc - datetime.now(tz=timezone.utc)
            #     <= text(f"interval '{forecast_horizon_minutes} minute'")
            # )

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
        national_forecast_values = [
            NationalForecastValue(
                target_time=forecast_value[0],
                expected_power_generation_megawatts=forecast_value[1],
                plevels={},
            )
            for forecast_value in forecast_values
        ]
        print("format", time.time() - t, "seconds", len(forecast_values))

        return national_forecast_values
    else:

        forecast_values = get_forecast_values(session=session,
                                              start_datetime_utc=start_datetime_utc,
                                              end_datetime_utc=end_datetime_utc,
                                              gsp_ids=[0])

        national_forecast_values = [
            NationalForecastValue(
                target_time=forecast_value[0],
                expected_power_generation_megawatts=forecast_value[1],
                plevels={},
            )
            for forecast_value in forecast_values]

        for national_forecast_value in national_forecast_values:
            format_plevels(national_forecast_value)

        return national_forecast_values

def get_forecast_values(
    session: Session,
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    gsp_ids: list[int] | None = None,
) -> list[()]:
    """Get forecast values from the database.

    We get all the latest forecast values for the blend model.
    We convert the sqlalchemy objects to OneDatetimeManyForecastValues
    Particular focus has been put on only get the data we need from the database.

    This function
    1. get model ids
    2. get forecast values from the forecast_value_latest table.
        We tried to only get the relevant data as needed, as this is normally a larger query

    return list of, 1. target_time, 2. expected_power_generation_megawatts, 3. gsp_id
    """
    # 1. get model ids
    model_ids = session.query(MLModelSQL.id).filter(MLModelSQL.name == "blend").all()
    model_ids = [model_id[0] for model_id in model_ids]

    # 2. get forecast values from database
    query = session.query(
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.expected_power_generation_megawatts.cast(NUMERIC(10, 2)),
        ForecastValueLatestSQL.gsp_id,
    )

    # distinct on target_time
    query = query.distinct(ForecastValueLatestSQL.gsp_id, ForecastValueLatestSQL.target_time)

    # join with model table
    query = query.filter(ForecastValueLatestSQL.model_id.in_(model_ids))

    # filters
    query = filter_start_and_end_datetime(
        query=query, start_datetime_utc=start_datetime_utc, end_datetime_utc=end_datetime_utc
    )
    query = filter_gsp_id(query=query, gsp_ids=gsp_ids)

    # order by target time and created utc desc
    query = query.order_by(
        ForecastValueLatestSQL.gsp_id,
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.created_utc.desc(),
    )

    forecast_values = query.all()

    return forecast_values

def get_forecast_values_all_compact(
        session: Session,
        start_datetime_utc: datetime | None = None,
        end_datetime_utc: datetime | None = None,
        gsp_ids: list[int] | None = None,
) -> list[OneDatetimeManyForecastValues]:
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

    # 1. and 2.
    forecast_values = get_forecast_values(session=session,
                                         start_datetime_utc=start_datetime_utc,
                                         end_datetime_utc=end_datetime_utc,
                                         gsp_ids=gsp_ids)

    # 3. convert to OneDatetimeManyForecastValues
    many_forecast_values_by_datetime = {}

    # loop over locations and gsp yields to create a dictionary of gsp generation by datetime
    for forecast_value in forecast_values:
        datetime_utc = forecast_value[0]
        power_kw = forecast_value[1]
        gsp_id = forecast_value[2]

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


def filter_gsp_id(query: Query, gsp_ids: list | None, model=ForecastValueLatestSQL):
    """Filter by gsp id."""
    if gsp_ids is not None:
        query = query.filter(model.gsp_id.in_(gsp_ids))
    else:
        # dont get gps id 0
        query = query.filter(model.gsp_id != 0)
    return query


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


def get_forecasts_and_forecast_values(
    session: Session,
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    gsp_ids=None,
) -> ManyForecasts:
    """Get forecast from the database.

    We get all the latest forecast values for the blend model.
    We convert the sqlalchemy objects to ManyForecasts
    Particular focus has been put on only get the data we need from the database.

    This function
    1. get model ids
    2. get forecast values from the forecast_value_latest table.
        We tried to only get the relevant data as needed, as this is normally a larger query
    3. get the forecasts we need
    4. Convert to Forecast objects
    5. add forecast values to forecast objects. We normalize the power,
        and do the adjuster for gsp_id=0
    6. convert to ManyForecasts

    :param session: database session
    :param start_datetime_utc: start datetime
    :param end_datetime_utc: end datetime
    :param gsp_ids: list of gsp ids
    :return: ManyForecasts object
    """

    # 1. get model ids
    model_ids = session.query(MLModelSQL.id).filter(MLModelSQL.name == "blend").all()
    model_ids = [model_id[0] for model_id in model_ids]

    # 2. get forecast values from database
    columns = [
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.expected_power_generation_megawatts.cast(NUMERIC(10, 2)),
        ForecastValueLatestSQL.gsp_id,
    ]

    if gsp_ids is not None and 0 in gsp_ids:
        columns.append(ForecastValueLatestSQL.adjust_mw)

    query = session.query(*columns)

    # distinct on target_time
    query = query.distinct(ForecastValueLatestSQL.gsp_id, ForecastValueLatestSQL.target_time)

    # join with model table
    query = query.filter(ForecastValueLatestSQL.model_id.in_(model_ids))

    # filters
    query = filter_start_and_end_datetime(
        query=query, start_datetime_utc=start_datetime_utc, end_datetime_utc=end_datetime_utc
    )
    query = filter_gsp_id(query=query, gsp_ids=gsp_ids)

    # order by target time and created utc desc
    query = query.order_by(
        ForecastValueLatestSQL.gsp_id,
        ForecastValueLatestSQL.target_time,
        ForecastValueLatestSQL.created_utc.desc(),
    )

    forecast_values = query.all()

    # 3. get forecasts
    query = session.query(
        ForecastSQL.forecast_creation_time,
        ForecastSQL.initialization_datetime_utc,
        LocationSQL.gsp_id,
        LocationSQL.gsp_name,
        LocationSQL.gsp_group,
        LocationSQL.region_name,
        LocationSQL.installed_capacity_mw,
        LocationSQL.label,
        MLModelSQL.name,
        MLModelSQL.version,
        InputDataLastUpdatedSQL.gsp,
        InputDataLastUpdatedSQL.nwp,
        InputDataLastUpdatedSQL.pv,
        InputDataLastUpdatedSQL.satellite,
    )

    # only get historic forecasts
    query = query.filter(ForecastSQL.historic == True)  # noqa E712

    # join with location tables
    query = query.join(LocationSQL)
    query = query.join(MLModelSQL)
    query = query.join(InputDataLastUpdatedSQL)

    # filters
    query = filter_gsp_id(gsp_ids=gsp_ids, query=query, model=LocationSQL)
    query = query.filter(ForecastSQL.model_id.in_(model_ids))

    # order by gsp_id
    query = query.order_by(LocationSQL.gsp_id)

    forecasts = query.all()

    # 4. Convert to Forecast objects
    forecast_objects = {}
    for forecast in forecasts:
        forecast_creation_time = forecast[0]
        initialization_datetime_utc = forecast[1]
        gsp_id = forecast[2]

        # creation Location object
        location = Location(
            gsp_id=gsp_id,
            gsp_name=forecast[3],
            gsp_group=forecast[4],
            region_name=forecast[5],
            installed_capacity_mw=forecast[6],
            label=forecast[7],
        )

        # create model object
        model = MLModel(name=forecast[8], version=forecast[9])

        # create input last update object
        input_data_last_updated = InputDataLastUpdated(
            gsp=forecast[10],
            nwp=forecast[11],
            pv=forecast[12],
            satellite=forecast[13],
        )
        forecast_py = Forecast(
            historic=True,
            forecast_creation_time=forecast_creation_time,
            initialization_datetime_utc=initialization_datetime_utc,
            forecast_values=[],
            location=location,
            model=model,
            input_data_last_updated=input_data_last_updated,
        )
        forecast_objects[gsp_id] = forecast_py

    # 5. add forecast values to forecast objects
    for forecast_value in forecast_values:
        datetime_utc = forecast_value[0]
        power_mw = forecast_value[1]
        gsp_id = forecast_value[2]

        if gsp_id in forecast_objects:
            installed_capacity_mw = forecast_objects[gsp_id].location.installed_capacity_mw

            if installed_capacity_mw > 0:
                normalized_power = round(
                    float(power_mw) / forecast_objects[gsp_id].location.installed_capacity_mw, 2
                )
            else:
                normalized_power = power_mw

            fv = ForecastValue(
                target_time=datetime_utc,
                expected_power_generation_megawatts=power_mw,
                expected_power_generation_normalized=normalized_power,
            )

            if gsp_id == 0:
                fv._adjust_mw = forecast_value[3]
                fv = fv.adjust(limit=adjust_limit)

            forecast_objects[gsp_id].forecast_values.append(fv)

    # 6. convert to ManyForecasts
    return ManyForecasts(forecasts=list(forecast_objects.values()))


