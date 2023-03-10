""" Test for main app """

from freezegun import freeze_time
from nowcasting_datamodel.read.read import national_gb_label

from database import get_forecasts_for_a_specific_gsp_from_database, get_gsp_system, get_session


def test_get_session():
    """Check get session works"""
    _ = next(get_session())


@freeze_time("2022-01-01")
def test_get_forecasts_for_a_specific_gsp_from_database(db_session, forecasts):
    """Check main route works"""

    gsp_id = 1

    _ = get_forecasts_for_a_specific_gsp_from_database(gsp_id=gsp_id, session=db_session)



def test_get_gsp_system_all(db_session, forecasts):
    """Check get gsp system works for all systems"""
    a = get_gsp_system(session=db_session)
    assert len(a) == 338


def test_get_gsp_system_one(db_session, forecasts):
    """Check get gsp system works for one system"""
    a = get_gsp_system(session=db_session, gsp_id=1)
    assert len(a) == 1


def test_get_gsp_system_one_national(db_session, forecasts):
    """Check get gsp system works for one system"""
    a = get_gsp_system(session=db_session, gsp_id=0)
    assert len(a) == 1
    assert a[0].label == national_gb_label
