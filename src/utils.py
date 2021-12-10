""" Utils functions for main.py """
from datetime import datetime, timedelta

import numpy as np


def datetime_must_have_timezone(cls, v: datetime):
    """Enforce that this variable must have a timezone"""
    if v.tzinfo is None:
        raise ValueError(f"{v} must have a timezone, for cls {cls}")
    return v


def convert_to_camelcase(snake_str: str) -> str:
    """Converts a given snake_case string into camelCase"""
    first, *others = snake_str.split("_")
    return "".join([first.lower(), *map(str.title, others)])


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
