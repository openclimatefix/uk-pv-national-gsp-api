""" Main FastAPI app """
from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

version = '0.1'

app = FastAPI(title="NowcastingApp",
              version=version,
              contact={"name": "Open Climate Fix"})

thirty_minutes = timedelta(minutes=30)


class OneForecast(BaseModel):
    """ One Forecast of generation at one timestamp """
    generation_mw: float
    datetime_utc: datetime


class OneGSP(BaseModel):
    """ Forecast for one gsp, there are forecast for several timestamps """
    gsp_id: int
    forecasts: List[OneForecast]


class MultipleGSP(BaseModel):
    """ Forecasts for multiple GSP """
    gsps: List[OneGSP]


@app.get("/")
def read_root():
    """ Default root """
    return {"title": "Nowcasting Forecast",
            "version": version,
            "documentation": " go to /docs/ to see documentation"}


@app.get("/v0/latest/", response_model=MultipleGSP)
def get_latest() -> MultipleGSP:
    """
    Current this produces a dummy array

    :return: Forecast of solar generation for different gsp for the next 2 hours
    """
    # get datetime right now
    now = datetime.now(timezone.utc)
    now_floor_30 = floor_30_minutes_dt(dt=now)

    # make list of datetimes that the forecast is for
    datetimes_utc = [now_floor_30 + i * thirty_minutes for i in range(4)]

    # create a list of forecasts
    forecasts = [
        OneForecast(generation_mw=0, datetime_utc=datetime_utc) for datetime_utc in datetimes_utc
    ]

    # make forecasts for all gsps
    multiple_gsp = [OneGSP(forecasts=forecasts, gsp_id=gsp_id) for gsp_id in range(1, 340)]
    multiple_gsp = MultipleGSP(gsps=multiple_gsp)

    return multiple_gsp


def floor_30_minutes_dt(dt):
    """
    Floor a datetime by 30 mins.

    For example:
    2021-01-01 17:01:01 --> 2021-01-01 17:00:00
    2021-01-01 17:35:01 --> 2021-01-01 17:30:00

    :param dt:
    :return:
    """
    approx = np.floor(dt.minute / 30.0) * 30
    dt = dt.replace(minute=0)
    dt = dt.replace(second=0)
    dt = dt.replace(microsecond=0)
    dt += timedelta(minutes=approx)

    return dt
