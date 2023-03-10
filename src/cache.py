import os
import logging
import json
from functools import wraps
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)

CACHE_TIME_SECONDS = 120
cache_time_seconds = int(os.getenv('CACHE_TIME_SECONDS', CACHE_TIME_SECONDS))


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
    async def wrapper(*args, **kwargs):
        nonlocal response
        nonlocal last_updated

        route_variables = kwargs.copy()
        route_variables.pop('session')
        route_variables.pop('user')
        route_variables = json.dumps(route_variables)

        if route_variables not in last_updated:
            logger.debug('First time this is route run')
            last_updated[route_variables] = datetime.now(tz=timezone.utc)
            response[route_variables] = await func(*args, **kwargs)
            return response[route_variables]

        now = datetime.now(tz=timezone.utc)
        if now - timedelta(seconds=cache_time_seconds) > last_updated[route_variables]:
            logger.debug(f'not using cache as longer than {cache_time_seconds} seconds')
            last_updated[route_variables] = now
            response[route_variables] = await func(*args, **kwargs)
            return response[route_variables]

        logger.debug('Using cache route')
        return response[route_variables]

    return wrapper
