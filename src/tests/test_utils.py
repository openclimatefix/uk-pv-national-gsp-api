""" Utils functions for test """

import os
from datetime import datetime, timezone

from freezegun import freeze_time

from pydantic_models import NationalForecastValue
from utils import floor_30_minutes_dt, format_plevels, get_start_datetime, traces_sampler

LOWER_LIMIT_MINUTE = 0
UPPER_LIMIT_MINUTE = 60


def get_every_minute():
    """
    Generate every possible minute in an hour time frame

    Example: Start with current hour when program is run, so for example the
    current hour is 12:05:18, it will reset to 12:00:18 and add to list every minute
    for that hour so at the end list look like this
    [12:00:18, 12:01:18, 12:02:18 ... 12:59:18]

    Returns:
        list: list containing current hour with every possible minute
    """
    time_now = datetime.now(timezone.utc)
    list_of_times = []
    minutes = 0
    while (minutes >= LOWER_LIMIT_MINUTE) and (minutes < UPPER_LIMIT_MINUTE):
        time_minutes = time_now.replace(minute=minutes)
        list_of_times.append(time_minutes)
        minutes += 1
    return list_of_times


def test_floor_30_minutes():
    """
    Test if floor_30_minutes_dt method works by testing against every minute in a hour

    For minutes in range [0, 30) => Will floor to 0 minutes
    For minutes in range [30, 60) => Will floor to 30 minutes
    """
    list_of_time = get_every_minute()
    input = datetime.fromisoformat("2021-09-30 12:15:05")
    expected_output = datetime.fromisoformat("2021-09-30 12:00:00")

    assert floor_30_minutes_dt(input) == expected_output  # Basic control test

    for time in list_of_time:
        floor_minute = floor_30_minutes_dt(time)
        if time.minute < 30:
            assert floor_minute.minute == 0
        else:
            assert floor_minute.minute == 30


@freeze_time("2022-11-12 13:34:56")
def test_get_start_datetime():
    """Test that we get the correct start datetime"""

    # check yesterday
    assert (
        get_start_datetime().isoformat() == datetime(2022, 11, 11, tzinfo=timezone.utc).isoformat()
    )

    # check to data 10 days ago, + round down to 6 hours
    assert (
        get_start_datetime(n_history_days="10").isoformat()
        == datetime(2022, 11, 2, 12, tzinfo=timezone.utc).isoformat()
    )


@freeze_time("2022-06-12 13:34:56")
def test_get_start_datetime_summer():
    """Test that we get the correct start datetime"""

    # check yesterday
    assert (
        get_start_datetime().isoformat()
        == datetime(2022, 6, 10, 23, tzinfo=timezone.utc).isoformat()
    )

    # check to data 10 days ago, + round down to closest 6 hours, adjusting for BST
    assert (
        get_start_datetime(n_history_days="6").isoformat()
        == datetime(2022, 6, 6, 11, tzinfo=timezone.utc).isoformat()
    )


def test_traces_sampler():
    os.environ["ENVIRONMENT"] = "local"
    assert traces_sampler({}) == 0.0

    os.environ["ENVIRONMENT"] = "test"
    assert (
        traces_sampler({"parent_sampled": False, "transaction_context": {"name": "warning"}})
        == 0.05
    )
    assert (
        traces_sampler({"parent_sampled": True, "transaction_context": {"name": "warning"}}) == 0.0
    )
    assert (
        traces_sampler({"parent_sampled": False, "transaction_context": {"name": "error1"}}) == 1.0
    )


def test_format_plevels():
    """Make sure dummy plevels are made correctly"""
    fv = NationalForecastValue(
        expected_power_generation_megawatts=1.0,
        target_time=datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

    format_plevels(national_forecast_value=fv)
    fv.plevels = {"10": 0.8, "90": 1.2}
