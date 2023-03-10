import json
import logging
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

logger = logging.getLogger(__name__)

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
    def wrapper(*args, **kwargs):
        nonlocal response
        nonlocal last_updated

        # get teh variables that go into the route
        # we don't want to use the cache for different variables
        route_variables = kwargs.copy()

        # drop session and user
        for var in ["session", "user"]:
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
            last_updated[route_variables] = now
            response[route_variables] = func(*args, **kwargs)
            return response[route_variables]

        # use cache
        logger.debug("Using cache route")
        return response[route_variables]

    return wrapper
