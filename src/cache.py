""" Caching utils for api"""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import structlog

from database import save_api_call_to_db

logger = structlog.stdlib.get_logger()

CACHE_TIME_SECONDS = 120
cache_time_seconds = int(os.getenv("CACHE_TIME_SECONDS", CACHE_TIME_SECONDS))
DELETE_CACHE_TIME_SECONDS = 240
delete_cache_time_seconds = int(os.getenv("DELETE_CACHE_TIME_SECONDS", DELETE_CACHE_TIME_SECONDS))


def remove_old_cache(
    last_updated: dict, response: dict, remove_cache_time_seconds: float = delete_cache_time_seconds
):
    """
    Remove old cache entries from the cache

    :param last_updated: dict of last updated times
    :param response: dict of responses, same keys as last_updated
    :param remove_cache_time_seconds: the amount of time, after which the cache should be removed
    """
    now = datetime.now(tz=timezone.utc)
    logger.info("Removing old cache entries")
    keys_to_remove = []
    for key, value in last_updated.items():
        if now - timedelta(seconds=remove_cache_time_seconds) > value:
            logger.debug(f"Removing {key} from cache, ({value})")
            keys_to_remove.append(key)

    for key in keys_to_remove:
        last_updated.pop(key)
        response.pop(key)

    return last_updated, response


def cache_response(func):
    """
    Decorator that caches the response of a FastAPI async function.

    Example:
    ```
        app = FastAPI()

        @app.get("/")
        @cache_response
        async def example():
            return {"message": "Hello World"}
    ```
    """
    response = {}
    last_updated = {}

    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa
        nonlocal response
        nonlocal last_updated

        # get the variables that go into the route
        # we don't want to use the cache for different variables
        route_variables = kwargs.copy()

        # save route variables to db
        session = route_variables.get("session", None)
        user = route_variables.get("user", None)
        request = route_variables.get("request", None)
        save_api_call_to_db(session=session, user=user, request=request)

        # drop session and user
        for var in ["session", "user", "request"]:
            if var in route_variables:
                route_variables.pop(var)

        last_updated, response = remove_old_cache(last_updated, response)

        # make route_variables into a string
        route_variables = json.dumps(route_variables)

        # check if its been called before
        if route_variables not in last_updated:
            logger.debug("First time this is route run")
            last_updated[route_variables] = datetime.now(tz=timezone.utc)
            response[route_variables] = func(*args, **kwargs)
            return response[route_variables]

        # re run if cache time out is up
        now = datetime.now(tz=timezone.utc)
        if now - timedelta(seconds=cache_time_seconds) > last_updated[route_variables]:
            logger.debug(f"not using cache as longer than {cache_time_seconds} seconds")
            response[route_variables] = func(*args, **kwargs)
            last_updated[route_variables] = now
            return response[route_variables]

        # re-run if response is not cached for some reason or is empty
        if route_variables not in response or response[route_variables] is None:
            logger.debug("not using cache as response is empty")
            attempt = 0
            # wait until response has been cached
            while attempt < 10:
                logger.debug(f"waiting for response to be cached, {attempt} seconds elapsed")
                time.sleep(1)
                attempt += 1
                if route_variables in response and response[route_variables] is not None:
                    logger.debug(
                        f"response cached after {attempt} seconds, returning cached response"
                    )
                    break
            if attempt >= 10:
                # if response is not in cache after 10 seconds, re-run
                logger.debug("response not cached after 10 seconds, re-running")
                response[route_variables] = func(*args, **kwargs)
                last_updated[route_variables] = now
                return response[route_variables]

        # use cache
        logger.debug("Using cache route")
        return response[route_variables]

    return wrapper
