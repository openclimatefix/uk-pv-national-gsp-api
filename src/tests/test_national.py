""" Test for main app """
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from freezegun import freeze_time
from nowcasting_datamodel.fake import (
    make_fake_national_forecast,
)
from nowcasting_datamodel.models import (
    Forecast,
    GSPYield,
    Location,
    LocationSQL,
)

from database import get_session
from main import app

client = TestClient(app)


def test_read_latest_national(db_session):
    """Check main solar/GB/national/forecast/ route works"""

    forecast = make_fake_national_forecast(session=db_session)
    db_session.add(forecast)

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/national/forecast/")
    assert response.status_code == 200

    _ = Forecast(**response.json())


@freeze_time("2022-01-01")
def test_read_truth_national_gsp(db_session):
    """Check main solar/GB/national/pvlive/ route works"""

    gsp_yield_1 = GSPYield(datetime_utc=datetime(2022, 1, 2), solar_generation_kw=1)
    gsp_yield_1_sql = gsp_yield_1.to_orm()

    gsp_yield_2 = GSPYield(datetime_utc=datetime(2022, 1, 1), solar_generation_kw=2)
    gsp_yield_2_sql = gsp_yield_2.to_orm()

    gsp_yield_3 = GSPYield(datetime_utc=datetime(2022, 1, 1, 12), solar_generation_kw=3)
    gsp_yield_3_sql = gsp_yield_3.to_orm()

    gsp_sql_1: LocationSQL = Location(
        gsp_id=0, label="national", status_interval_minutes=5
    ).to_orm()

    # add pv system to yield object
    gsp_yield_1_sql.location = gsp_sql_1
    gsp_yield_2_sql.location = gsp_sql_1
    gsp_yield_3_sql.location = gsp_sql_1

    # add to database
    db_session.add_all([gsp_yield_1_sql, gsp_yield_2_sql, gsp_yield_3_sql, gsp_sql_1])

    app.dependency_overrides[get_session] = lambda: db_session

    response = client.get("/v0/solar/GB/national/pvlive/")
    assert response.status_code == 200

    r_json = response.json()
    assert len(r_json) == 3
    _ = [GSPYield(**gsp_yield) for gsp_yield in r_json]
