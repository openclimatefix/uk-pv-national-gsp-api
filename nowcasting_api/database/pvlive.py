"""Get PVLive data from the database."""

from datetime import datetime

from nowcasting_datamodel.models.gsp import GSPYield, GSPYieldSQL, Location, LocationSQL
from pydantic_models import GSPYieldGroupByDatetime, LocationWithGSPYields
from sqlalchemy import NUMERIC
from sqlalchemy.orm import Session
from utils import get_start_datetime


def get_gsp_yield_values(
    session: Session,
    regime: str | None = "in-day",
    start_datetime_utc: datetime | None = None,
    end_datetime_utc: datetime | None = None,
    compact: bool | None = False,
    gsp_ids: list[int] | None = None,
) -> list[LocationWithGSPYields] | list[GSPYieldGroupByDatetime]:
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

    start_datetime_utc = get_start_datetime(start_datetime=start_datetime_utc)
    if regime is None:
        regime = "in-day"

    # start main query
    query = session.query(
        GSPYieldSQL.datetime_utc,
        GSPYieldSQL.solar_generation_kw.cast(NUMERIC(10, 2)),
        LocationSQL.gsp_id,
    )

    # only select on results per gsp
    query = query.distinct(LocationSQL.gsp_id, GSPYieldSQL.datetime_utc)

    # filter on gsps
    query = query.join(LocationSQL)
    # filter on gsp_ids
    if gsp_ids is not None:
        query = query.where(LocationSQL.gsp_id.in_(gsp_ids))
    else:
        # dont get gsp_id =0
        query = query.where(LocationSQL.gsp_id != 0)

    # filter on regime
    if regime is not None:
        query = query.where(GSPYieldSQL.regime == regime)

    # filter on datetime
    query = query.where(GSPYieldSQL.datetime_utc >= start_datetime_utc)
    if end_datetime_utc is not None:
        query = query.where(GSPYieldSQL.datetime_utc <= end_datetime_utc)

    # don't get any nans. (Note nan+1 > nan = False)
    query = query.where(GSPYieldSQL.solar_generation_kw + 1 > GSPYieldSQL.solar_generation_kw)

    # order by gsp_id, datetime_utc
    # and created_utc
    query = query.order_by(
        LocationSQL.gsp_id, GSPYieldSQL.datetime_utc, GSPYieldSQL.created_utc.desc()
    )

    gsp_yields = query.all()

    # format the results
    if compact:
        gsp_yields_grouped_by_datetime_pydantic = convert_to_gsp_yields_grouped_by_datetimes(
            gsp_yields
        )
        return gsp_yields_grouped_by_datetime_pydantic

    else:

        query = session.query(LocationSQL)
        if gsp_ids is not None:
            query = query.where(LocationSQL.gsp_id.in_(gsp_ids))
        else:
            query = query.where(LocationSQL.gsp_id != 0)
        query = query.order_by(LocationSQL.gsp_id)
        locations = query.all()
        locations = [Location.from_orm(location) for location in locations]

        locations_with_gsp_yields = convert_to_locations_with_gsp_yields(
            gsp_yields, locations, regime
        )

        return locations_with_gsp_yields


def convert_to_locations_with_gsp_yields(
    gsp_yields, locations, regime
) -> list[LocationWithGSPYields]:
    """Convert gsp_yields and locations to a list of LocationWithGSPYields objects.

    :param gsp_yields: list of [datetime_utc, solar_generation_kw, gps_id]
    :param locations: list of Location objects
    :param regime: regime string, e.g. "in-day" or "day-after"

    :return list of LocationWithGSPYields objects
    """
    # create a mapping from gsp_id to location
    gsp_id_to_location = {location.gsp_id: location for location in locations}
    gsp_yields_grouped_by_gsp_id = {}
    for gsp_yield in gsp_yields:
        datetime_utc = gsp_yield[0]
        solar_generation_kw = gsp_yield[1]
        gsp_id = gsp_yield[2]

        gsp_yield = GSPYield(
            datetime_utc=datetime_utc,
            solar_generation_kw=solar_generation_kw,
            regime=regime,
        )

        # if the gsp_id object is not in the dictionary, add it
        if gsp_id not in gsp_yields_grouped_by_gsp_id:
            gsp_yields_grouped_by_gsp_id[gsp_id] = [gsp_yield]
        else:
            gsp_yields_grouped_by_gsp_id[gsp_id].append(gsp_yield)
    # convert dictionary to list of LocationWithGSPYields objects
    locations_with_gsp_yields = []
    for gsp_id, gsp_yields in gsp_yields_grouped_by_gsp_id.items():
        location = gsp_id_to_location[gsp_id]
        locations_with_gsp_yields.append(
            LocationWithGSPYields(
                gsp_id=gsp_id,
                gsp_yields=gsp_yields,
                label=location.label,
                gsp_name=location.gsp_name,
                gsp_group=location.gsp_group,
                region_name=location.region_name,
                installed_capacity_mw=location.installed_capacity_mw,
            )
        )
    return locations_with_gsp_yields


def convert_to_gsp_yields_grouped_by_datetimes(gsp_yields) -> list[GSPYieldGroupByDatetime]:
    """Convert gsp_yields to a list of GSPYieldGroupByDatetime objects.

    :param gsp_yields: list of [datetime_utc, solar_generation_kw, gps_id]
    :return list of LocationWithGSPYields objects
    """

    # process results into GSPYieldGroupByDatetime
    gsp_yields_grouped_by_datetime = {}
    for gsp_yield in gsp_yields:
        datetime_utc = gsp_yield[0]
        solar_generation_kw = gsp_yield[1]
        gsp_id = gsp_yield[2]

        # if the datetime object is not in the dictionary, add it
        if datetime_utc not in gsp_yields_grouped_by_datetime:
            gsp_yields_grouped_by_datetime[datetime_utc] = {gsp_id: solar_generation_kw}
        else:
            gsp_yields_grouped_by_datetime[datetime_utc][gsp_id] = solar_generation_kw
    # convert dictionary to list of OneDatetimeGSPGeneration objects
    gsp_yields_grouped_by_datetime_pydantic = []
    for datetime_utc, gsp_yields in gsp_yields_grouped_by_datetime.items():
        gsp_yields_grouped_by_datetime_pydantic.append(
            GSPYieldGroupByDatetime(datetime_utc=datetime_utc, generation_kw_by_gsp_id=gsp_yields)
        )
    return gsp_yields_grouped_by_datetime_pydantic
