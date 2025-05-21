"""Get data from database - optimized"""

from datetime import datetime

from nowcasting_datamodel.models import ForecastValueLatestSQL, MLModelSQL
from pydantic_models import OneDatetimeManyForecastValues
from sqlalchemy.orm.session import Session


def get_forecast_values_all_compact(
    session: Session,
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    gsp_ids: list[str] | None = None,
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
        # dont get gsp id 0
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
