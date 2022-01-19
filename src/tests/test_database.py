""" Test for main app """

from database import get_forecasts_for_a_specific_gsp_from_database, get_session


def test_get_session():
    """Check get session works"""
    _ = next(get_session())


def test_get_forecasts_for_a_specific_gsp_from_database(db_session, forecasts):
    """Check main route works"""

    gsp_id = 1

    _ = get_forecasts_for_a_specific_gsp_from_database(gsp_id=gsp_id, session=db_session)
