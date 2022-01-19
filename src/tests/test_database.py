""" Test for main app """

from fastapi.testclient import TestClient

from main import app, version
from database import get_forecasts_for_a_specific_gsp_from_database
from nowcasting_forecast.database.fake import make_fake_forecasts

client = TestClient(app)


def test_get_forecasts_for_a_specific_gsp_from_database(db_session, forecasts):
    """Check main route works"""

    gsp_id = 1

    _ = get_forecasts_for_a_specific_gsp_from_database(gsp_id=gsp_id, session=db_session)
