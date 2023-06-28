""" Caching utils for api"""
import json
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import structlog

from database import save_api_call_to_db

logger = structlog.stdlib.get_logger()

CACHE_TIME_SECONDS = 120
cache_time_seconds = int(os.getenv("CACHE_TIME_SECONDS", CACHE_TIME_SECONDS))


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

        # make into string
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

        # use cache
        logger.debug("Using cache route")
        return response[route_variables]

    return wrapper
