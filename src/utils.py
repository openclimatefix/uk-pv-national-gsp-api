""" Utils functions for main.py """
import structlog
import os
from datetime import datetime, timedelta
from typing import Optional, Union

import numpy as np
from nowcasting_datamodel.models import ForecastValue
from pydantic import Field
from pytz import timezone

logger = structlog.stdlib.get_logger()

europe_london_tz = timezone("Europe/London")
utc = timezone("UTC")


class NationalForecastValue(ForecastValue):
    """One Forecast of generation at one timestamp include properties"""

    plevels: dict = Field(
        None, description="Dictionary to hold properties of the forecast, like p_levels. "
    )


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


def traces_sampler(sampling_context):
    """
    Filter tracing for sentry logs.

    Examine provided context data (including parent decision, if any)
    along with anything in the global namespace to compute the sample rate
    or sampling decision for this transaction
    """

    if os.getenv("ENVIRONMENT") == "local":
        return 0.0
    elif "error" in sampling_context["transaction_context"]["name"]:
        # These are important - take a big sample
        return 1.0
    elif sampling_context["parent_sampled"] is True:
        # These aren't something worth tracking - drop all transactions like this
        return 0.0
    else:
        # Default sample rate
        return 0.05


def format_plevels(national_forecast_value: NationalForecastValue):
    """
    Format the plevels dictionary to have the correct keys.

    1. if None set to default
    2. rename 10 and 90 to plevel_10 and plevel_90
    3. if 10 or 90 is None set to default

    :param national_forecast_value:
    :return:
    """
    logger.debug(f"{national_forecast_value.plevels}")
    if (not isinstance(national_forecast_value.plevels, dict)) or (
        national_forecast_value.plevels == {}
    ):
        logger.warning(f"Using default properties for {national_forecast_value.__fields__.keys()}")
        national_forecast_value.plevels = {
            "plevel_10": national_forecast_value.expected_power_generation_megawatts * 0.8,
            "plevel_90": national_forecast_value.expected_power_generation_megawatts * 1.2,
        }
        logger.debug(f"{national_forecast_value.plevels}")

    # rename '10' and '90' to plevel_10 and plevel_90
    for c in ["10", "90"]:
        if c in national_forecast_value.plevels.keys():
            national_forecast_value.plevels[f"plevel_{c}"] = national_forecast_value.plevels.pop(c)

    if national_forecast_value.plevels["plevel_10"] is None:
        logger.debug("Setting plevel_10 to default")
        national_forecast_value.plevels["plevel_10"] = (
            national_forecast_value.expected_power_generation_megawatts * 0.8
        )

    if national_forecast_value.plevels["plevel_90"] is None:
        logger.debug("Setting plevel_90 to default")
        national_forecast_value.plevels["plevel_90"] = (
            national_forecast_value.expected_power_generation_megawatts * 1.2
        )
