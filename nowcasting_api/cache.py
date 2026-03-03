""" Caching utils for api"""

import json
import os
import time
from functools import wraps

import structlog
from apitally.fastapi import set_consumer
from cachetools import TTLCache
from fastapi.encoders import jsonable_encoder

logger = structlog.stdlib.get_logger()

CACHE_TIME_SECONDS = 120
cache_time_seconds = int(os.getenv("CACHE_TIME_SECONDS", CACHE_TIME_SECONDS))

QUERY_WAIT_SECONDS = int(os.getenv("QUERY_WAIT_SECONDS", 30))


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
    cache = TTLCache(maxsize=128, ttl=cache_time_seconds)
    currently_running = {}

    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa
        nonlocal cache
        nonlocal currently_running

        # get the variables that go into the route
        # we don't want to use the cache for different variables
        route_variables = kwargs.copy()

        user = route_variables.get("user", None)
        request = route_variables.get("request", None)

        # set Apitally consumer for per-user metrics
        if user is not None and request is not None:
            set_consumer(request, identifier=user.email if hasattr(user, "email") else "unknown")

        # get permissions from user to include in cache key
        if user is not None and hasattr(user, "permissions"):
            permissions = user.permissions
            route_variables["permissions"] = permissions

        # drop non-serializable objects from cache key
        for var in ["session", "user", "request"]:
            if var in route_variables:
                route_variables.pop(var)

        # make route_variables into a string\
        # TODO add url
        # TODO sort route variables alphabetically
        # url = request.url
        route_variables = json.dumps(route_variables)

        cache.expire()
        logger.info(
            "Cache stats",
            cache_size=len(cache),
            cache_maxsize=cache.maxsize,
            currently_running_keys=len(currently_running),
            cache_memory=cache.currsize,
        )

        # use case
        # A. First time we call this the route -> call the route (1.1)
        # B. Second time we call the route, but its running at the moment.
        #   Wait for it to finish. (1.0)
        # C. [removed] The cached result it old, and its not running, --> call the route (1.2)
        # D. The cached result is empty, and its running, --> (1.0)
        # E. The cached result is up to date, --> use the cache (1.4)
        # F. It is current being run, wait a bit, then try to use those results (1.0)
        # G. [removed] If the cache results is None, lets wait a few seconds,
        #   then try to use the cache (1.3)

        # 1.0
        if currently_running.get(route_variables, False):
            logger.debug("1.0 Route is being called somewhere else, so waiting for it to finish")
            attempt = 0
            while attempt < QUERY_WAIT_SECONDS:
                logger.debug(f"waiting for route to finish, {attempt} seconds elapsed")
                time.sleep(1)
                attempt += 1
                if not currently_running.get(route_variables, False):
                    logger.debug(
                        f"route finished after {attempt} seconds, returning cached response"
                    )
                    if route_variables in cache:
                        return cache[route_variables]
                    else:
                        logger.warning(
                            "Process finished running but response not "
                            "in cache. Setting this route as not running, "
                            "and continuing"
                        )
                        currently_running.pop(route_variables, None)
                        break

            logger.warning(
                f"Waited {QUERY_WAIT_SECONDS} seconds but response not "
                f"in cache. Setting this route as not running, "
                f"and continuing"
            )
            currently_running.pop(route_variables, None)

        # 1.1 check if its been called before and not currently running
        if (route_variables not in cache) and (not currently_running.get(route_variables, False)):
            logger.debug("1.1 First time this is route run, and not running now")

            # run the route
            currently_running[route_variables] = True
            try:
                result = func(*args, **kwargs)
                cache[route_variables] = jsonable_encoder(result)
                return result
            finally:
                currently_running.pop(route_variables, None)

        # 1.2 [removed cache staleness check as is now covered by TTLCache expiry]

        # 1.3 [removed because this logical route was due to last_updated + response dicts mismatch
        #      that is now handled by TTLCache internally]

        # 1.4 use cache
        logger.debug("Using cached response")
        return cache[route_variables]

    return wrapper
