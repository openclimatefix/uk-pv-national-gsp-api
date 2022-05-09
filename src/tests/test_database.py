""" Test for main app """

from database import get_forecasts_for_a_specific_gsp_from_database, get_session, get_gsp_system


def test_get_session():
    """Check get session works"""
    _ = next(get_session())


def test_get_forecasts_for_a_specific_gsp_from_database(db_session, forecasts):
    """Check main route works"""

    gsp_id = 1

    _ = get_forecasts_for_a_specific_gsp_from_database(gsp_id=gsp_id, session=db_session)


def test_get_gsp_system_none(db_session):
    a = get_gsp_system(session=db_session)
    assert len(a) == 0


def test_get_gsp_system_all(db_session,forecasts):
    a = get_gsp_system(session=db_session)
    assert len(a) == 338


def test_get_gsp_system_one(db_session,forecasts):
    a = get_gsp_system(session=db_session, gsp_id=1)
    assert len(a) == 1
