""" Utils functions for test """
from datetime import datetime, timezone

from utils import floor_30_minutes_dt

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
