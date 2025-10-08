""" Tests for the pvlive database functions.

Other tests are covered in test_gsp.py amd test_national.py
"""

from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from nowcasting_datamodel.models import GSPYield, Location, LocationSQL

from nowcasting_api.database.pvlive import get_gsp_yield_values
from nowcasting_api.pydantic_models import (GSPYieldGroupByDatetime,
                                            LocationWithGSPYields)


@pytest.fixture
def gsp_yields(db_session):
    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=122, label="GSP_122", status_interval_minutes=5
    ).to_orm()

    # add pv system to yield object
    gsp_yield_1_sql.location = gsp_sql_1
    gsp_yield_2_sql.location = gsp_sql_1
    gsp_yield_3_sql.location = gsp_sql_1

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_sql_1])
    db_session.commit()


@freeze_time("2022-01-02 12:10:00")
def test_get_gsp_yield_value(db_session, gsp_yields):

    location_with_gsp_yields: [LocationWithGSPYields] = get_gsp_yield_values(session=db_session)

    assert len(location_with_gsp_yields) == 1
    assert location_with_gsp_yields[0].gsp_id == 122
    assert len(location_with_gsp_yields[0].gsp_yields) == 3
    gsp_yields = location_with_gsp_yields[0].gsp_yields
    assert (
        gsp_yields[0].datetime_utc.isoformat()
        == datetime(2022, 1, 1, tzinfo=timezone.utc).isoformat()
    )
    assert gsp_yields[0].solar_generation_kw == 2
    assert (
        gsp_yields[1].datetime_utc.isoformat()
        == datetime(2022, 1, 1, 12, tzinfo=timezone.utc).isoformat()
    )
    assert gsp_yields[1].solar_generation_kw == 3
    assert (
        gsp_yields[2].datetime_utc.isoformat()
        == datetime(2022, 1, 2, tzinfo=timezone.utc).isoformat()
    )
    assert gsp_yields[2].solar_generation_kw == 1


@freeze_time("2022-01-02 12:10:00")
def test_get_gsp_yield_value_compact(db_session, gsp_yields):

    gsp_yields: [GSPYieldGroupByDatetime] = get_gsp_yield_values(session=db_session, compact=True)

    assert len(gsp_yields) == 3
    assert (
        gsp_yields[0].datetime_utc.isoformat()
        == datetime(2022, 1, 1, tzinfo=timezone.utc).isoformat()
    )
    assert gsp_yields[0].generation_kw_by_gsp_id[122] == 2
    assert (
        gsp_yields[1].datetime_utc.isoformat()
        == datetime(2022, 1, 1, 12, tzinfo=timezone.utc).isoformat()
    )
    assert gsp_yields[1].generation_kw_by_gsp_id[122] == 3
    assert (
        gsp_yields[2].datetime_utc.isoformat()
        == datetime(2022, 1, 2, tzinfo=timezone.utc).isoformat()
    )
    assert gsp_yields[2].generation_kw_by_gsp_id[122] == 1
