""" Test for main app """

from nowcasting_datamodel.fake import make_fake_forecasts
from nowcasting_datamodel.models import Location
from nowcasting_datamodel.read.read import get_location

from database import get_session
from main import app


def test_get_gsp_systems(db_session, api_client):
    """Check main system/GB/gsp/ works"""

    forecasts = make_fake_forecasts(gsp_ids=list(range(0, 10)), session=db_session)
    db_session.add_all(forecasts)
    db_session.commit()

    # update to installed capacity to a float
    location = get_location(
        gsp_id=1, session=db_session
    )
    location.installed_capacity_mw = 1.1
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("v0/system/GB/gsp/")
    assert response.status_code == 200

    locations = [Location(**location) for location in response.json()]
    assert len(locations) == 10
    assert locations[1].installed_capacity_mw == 1.1


def test_gsp_boundaries(db_session, api_client):
    """Check main system/GB/gsp/boundaries"""

    app.dependency_overrides[get_session] = lambda: db_session

    response = api_client.get("/v0/system/GB/gsp/boundaries")
    assert response.status_code == 200
    assert len(response.json()) > 0
