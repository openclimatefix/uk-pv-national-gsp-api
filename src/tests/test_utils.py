from datetime import datetime, timezone

# Used constants
LOWER_LIMIT_MINUTE = 0
UPPER_LIMIT_MINUTE = 60


def get_every_minute():
    """
    Generate every possible minute in an hour time frame and add every time with
    the possible minutes

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
    while minutes >= LOWER_LIMIT_MINUTE and minutes < UPPER_LIMIT_MINUTE:
        time_minutes = time_now.replace(minute=minutes)
        list_of_times.append(time_minutes)
        minutes += 1
    return list_of_times
