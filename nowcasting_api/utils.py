""" Utils functions for main.py """

import os
from datetime import datetime, timedelta
from typing import List, Optional, Union

import numpy as np
import structlog
from nowcasting_datamodel.models import Forecast
from pydantic_models import NationalForecastValue
from pytz import timezone
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = structlog.stdlib.get_logger()

europe_london_tz = timezone("Europe/London")
utc = timezone("UTC")

limiter = Limiter(key_func=get_remote_address)
N_CALLS_PER_HOUR = os.getenv("N_CALLS_PER_HOUR", 3600)  # 1 call per second
N_SLOW_CALLS_PER_MINUTE = os.getenv("N_SLOW_CALLS_PER_MINUTE", 1)  # 1 call per minute


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


def format_datetime(datetime_str: str = None):
    """
    Format datetime string to datetime object

    If None return None, if not timezone, add UTC
    :param datetime_str:
    :return:
    """
    if datetime_str is None:
        return None

    else:
        datetime_output = datetime.fromisoformat(datetime_str)
        if datetime_output.tzinfo is None:
            datetime_output = utc.localize(datetime_output)
        return datetime_output


def get_start_datetime(
    n_history_days: Optional[Union[str, int]] = None,
    start_datetime: Optional[datetime] = None,
    days: Optional[int] = 3,
) -> datetime:
    """
    Get the start datetime for the query

    By default we get yesterdays morning at midnight,
    we 'N_HISTORY_DAYS' use env var to get number of days

    :param n_history_days: n_history
    :param start_datetime: optional start datetime for the query.
     If not set, after now, or set to over three days ago
     defaults to N_HISTORY_DAYS env var, which defaults to yesterday.
    :param days: number of days limit the data by
    :return: start datetime
    """

    now = datetime.now(tz=utc)

    if start_datetime is None or now - start_datetime > timedelta(days=days):
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
    else:
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
    power = national_forecast_value.expected_power_generation_megawatts
    if (not isinstance(national_forecast_value.plevels, dict)) or (
        national_forecast_value.plevels == {}
    ):
        national_forecast_value.plevels = {
            "plevel_10": round(power * 0.8, 2),
            "plevel_90": round(power * 1.2, 2),
        }

        logger.info(f"plevels set to default: {national_forecast_value.plevels}")

    # rename '10' and '90' to plevel_10 and plevel_90
    for c in ["10", "90"]:
        if c in national_forecast_value.plevels.keys():
            national_forecast_value.plevels[f"plevel_{c}"] = round(
                national_forecast_value.plevels.pop(c), 2
            )

    if national_forecast_value.plevels["plevel_10"] is None:
        national_forecast_value.plevels["plevel_10"] = round(power * 0.8, 2)

    if national_forecast_value.plevels["plevel_90"] is None:
        national_forecast_value.plevels["plevel_90"] = round(power * 1.2, 2)


def filter_forecast_values(
    forecasts: List[Forecast],
    end_datetime_utc: Optional[datetime] = None,
    start_datetime_utc: Optional[datetime] = None,
) -> List[Forecast]:
    """
    Filter forecast values by start and end datetime

    :param forecasts: list of forecasts
    :param end_datetime_utc: start datetime
    :param start_datetime_utc: e
    :return:
    """
    if start_datetime_utc is not None or end_datetime_utc is not None:
        logger.info(f"Filtering forecasts from {start_datetime_utc} to {end_datetime_utc}")
        forecasts_filtered = []
        for forecast in forecasts:
            forecast_values = forecast.forecast_values
            if start_datetime_utc is not None:
                forecast_values = [
                    forecast_value
                    for forecast_value in forecast_values
                    if forecast_value.target_time >= start_datetime_utc
                ]
            if end_datetime_utc is not None:
                forecast_values = [
                    forecast_value
                    for forecast_value in forecast_values
                    if forecast_value.target_time <= end_datetime_utc
                ]
            forecast.forecast_values = forecast_values

            forecasts_filtered.append(forecast)
        forecasts = forecasts_filtered
    return forecasts
