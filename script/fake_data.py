"""
Fill database with fake data, so we can run this locally and the front end works

This is useful for when running the api locally with the front end

need to fill the following tables
1. forecast historic with forecast values
2. gsp yield with in-day and day-after amounts
3. a warning status of this is fake data
"""

import os
import sys
from datetime import UTC, datetime, timezone

from nowcasting_datamodel.connection import DatabaseConnection
from nowcasting_datamodel.fake import (
    N_FAKE_FORECASTS,
    generate_fake_forecasts,
    make_fake_gsp_yields,
)
from nowcasting_datamodel.models.forecast import (
    ForecastSQL,
    ForecastValueLatestSQL,
    ForecastValueSevenDaysSQL,
    ForecastValueSQL,
)
from nowcasting_datamodel.models.models import StatusSQL
from nowcasting_datamodel.save.save import save as save_forecasts
from sqlalchemy import inspect

from nowcasting_api.utils import floor_30_minutes_dt

# Add nowcasting_api to path for imports if using Docker.
# If running directly on local machine, this is not necessary, but runs without error.
sys.path.append("/app/nowcasting_api")

now = floor_30_minutes_dt(datetime.now(tz=timezone.utc))

if os.getenv("DB_URL") is None:
    raise ValueError("Please set the DB_URL environment variable")

if not os.getenv("DB_URL") == "postgresql://postgres:postgres@postgres:5432/postgres":
    raise ValueError("This script should only be run in the local docker container")

connection = DatabaseConnection(url=os.getenv("DB_URL", "not_set"))

print(f"Creating fake data at {now}")

# Check database has been created, if not run the migrations
if not inspect(connection.engine).has_table("status"):
    connection.create_all()


with connection.get_session() as session:
    session.query(StatusSQL).delete()
    # TODO: maybe only delete data older than 4hrs to keep N-hr forecasts but keep DB small
    session.query(ForecastValueSevenDaysSQL).delete()
    session.query(ForecastValueLatestSQL).delete()
    session.query(ForecastValueSQL).delete()
    session.query(ForecastSQL).delete()

    N_GSPS = 317

    # 1. make fake forecasts
    forecasts = generate_fake_forecasts(
        gsp_ids=range(0, N_GSPS),
        session=session,
        model_name="blend",
        t0_datetime_utc=floor_30_minutes_dt(datetime.now(tz=UTC)),
        add_latest=True,
        historic=True,
    )
    save_forecasts(forecasts, session)

    non_historic_forecasts = generate_fake_forecasts(
        gsp_ids=range(0, N_GSPS),
        session=session,
        model_name="blend",
        t0_datetime_utc=floor_30_minutes_dt(datetime.now(tz=UTC)),
        historic=False,
    )
    save_forecasts(non_historic_forecasts, session)

    # 2. make gsp yields
    make_fake_gsp_yields(gsp_ids=range(0, N_GSPS), session=session, t0_datetime_utc=now)

    # 3. make status
    status = StatusSQL(status="warning", message="Local Quartz API serving fake data")

    session.add(status)
    session.commit()

    assert len(session.query(StatusSQL).all()) == 1
    assert len(session.query(ForecastSQL).all()) == N_GSPS * 2
    assert len(session.query(ForecastValueLatestSQL).all()) == N_GSPS * N_FAKE_FORECASTS
    assert len(session.query(ForecastValueSQL).all()) == N_GSPS * N_FAKE_FORECASTS * 2
