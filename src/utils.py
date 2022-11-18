""" Utils functions for main.py """
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import numpy as np


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
        start_datetime = datetime.now(tz=timezone.utc).date() - timedelta(days=1)
        start_datetime = datetime.combine(start_datetime, datetime.min.time())
        start_datetime = start_datetime.replace(tzinfo=timezone.utc)
    else:
        start_datetime = datetime.now(tz=timezone.utc) - timedelta(days=int(n_history_days))
        start_datetime = floor_30_minutes_dt(start_datetime)
    return start_datetime
