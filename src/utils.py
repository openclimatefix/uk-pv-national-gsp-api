""" Utils functions for main.py """
import os
from datetime import datetime, timedelta
from typing import Optional, Union
from pytz import timezone

import numpy as np

import logging

logger = logging.getLogger(__name__)

europe_london_tz = timezone("Europe/London")
utc = timezone("UTC")


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


def floor_6_hours_dt(dt: datetime):
    """
    Floor a datetime by 6 hours.

    For example:
    2021-01-01 17:01:01 --> 2021-01-01 12:00:00
    2021-01-01 19:35:01 --> 2021-01-01 18:00:00

    :param dt: datetime
    :return: datetime rounded to lowest 6 hours
    """
    approx = np.floor(dt.hour / 6.0) * 6.0
    dt = dt.replace(hour=0)
    dt = dt.replace(minute=0)
    dt = dt.replace(second=0)
    dt = dt.replace(microsecond=0)
    dt += timedelta(hours=approx)

    return dt


def get_start_datetime(n_history_days: Optional[Union[str, int]] = None) -> datetime:
    """
    Get the start datetime for the query

    By default we get yesterdays morning at midnight,
    we 'N_HISTORY_DAYS' use env var to get number of days

    :param n_history_days: n_history
    :return: start datetime
    """

    if n_history_days is None:
        n_history_days = os.getenv("N_HISTORY_DAYS", "yesterday")

    # get at most 2 days of data.
    if n_history_days == "yesterday":
        start_datetime = datetime.now(tz=europe_london_tz).date() - timedelta(days=1)
        start_datetime = datetime.combine(start_datetime, datetime.min.time())
        start_datetime = europe_london_tz.localize(start_datetime)
        start_datetime = start_datetime.astimezone(utc)
    else:
        start_datetime = datetime.now(tz=europe_london_tz) - timedelta(days=int(n_history_days))
        start_datetime = floor_6_hours_dt(start_datetime)
        start_datetime = start_datetime.astimezone(utc)
    return start_datetime
