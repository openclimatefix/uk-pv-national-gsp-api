"""
Fill database with fake data, so we can run this locally and the front end works

This is useful for when running the api locally with the front end

need to fill the following tables
1. forecast historic with forecast values
2. gsp yield with in-day and day-after amounts
3. a warning status of this is fake data
"""

import os
from datetime import datetime, timezone

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.fake import make_fake_forecasts, make_fake_gsp_yields
from nowcasting_datamodel.models.forecast import (
    ForecastSQL,
    ForecastValueLatestSQL,
    ForecastValueSQL,
)
from nowcasting_datamodel.models.models import StatusSQL

from src.utils import floor_30_minutes_dt

now = floor_30_minutes_dt(datetime.now(tz=timezone.utc))

connection = DatabaseConnection(url=os.getenv("DB_URL", "not_set"))

with connection.get_session() as session:
    session.query(StatusSQL).delete()
    session.query(ForecastValueLatestSQL).delete()
    session.query(ForecastValueSQL).delete()
    session.query(ForecastSQL).delete()

    N_GSPS = 10

    # 1. make fake forecasts
    make_fake_forecasts(
        gsp_ids=range(0, N_GSPS),
        session=session,
        t0_datetime_utc=now,
        add_latest=True,
        historic=True,
    )

    # 2. make gsp yields
    make_fake_gsp_yields(gsp_ids=range(0, N_GSPS), session=session, t0_datetime_utc=now)

    # 3. make status
    status = StatusSQL(status="warning", message="this is all fake data")

    session.add(status)
    session.commit()

    assert len(session.query(StatusSQL).all()) == 1
    assert len(session.query(ForecastValueLatestSQL).all()) == 112 * N_GSPS
    assert len(session.query(ForecastValueSQL).all()) == 112 * N_GSPS
    assert len(session.query(ForecastSQL).all()) == N_GSPS
