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

N_ATTEMPTS = int(os.getenv("N_ATTEMPTS", 10))


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
    logger.info("Checking and removing old cache entries")
    keys_to_remove = []
    last_updated_copy = last_updated.copy()
    for key, value in last_updated_copy.items():
        if now - timedelta(seconds=remove_cache_time_seconds) > value:
            logger.debug(f"Removing {key} from cache, ({value})")
            keys_to_remove.append(key)

    del last_updated_copy
    logger.debug(f"Removing {len(keys_to_remove)} keys from cache")

    for key in keys_to_remove:
        try:
            last_updated.pop(key)
            response.pop(key)
        except KeyError:
            logger.warning(
                f"Could not remove {key} from cache. "
                f"This could be because it has already been removed"
            )

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
    currently_running = {}

    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa
        nonlocal response
        nonlocal last_updated
        nonlocal currently_running

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

        # use case
        # A. First time we call this the route -> call the route (1.1)
        # B. Second time we call the route, but its running at the moment.
        #   Wait for it to finish. (1.0)
        # C. The cached result it old, and its not running, --> call the route (1.2)
        # D. The cached result is empty, and its running, --> (1.0)
        # E. The cached result is up to date, --> use the cache (1.4)
        # F. It is current being run, wait a bit, then try to use those results (1.0)
        # G. If the cache results is None, lets wait a few seconds,
        #   then try to use the cache (1.3)

        # 1.0
        if currently_running.get(route_variables, False):
            logger.debug("Route is being called somewhere else, so waiting for it to finish")
            attempt = 0
            while attempt < N_ATTEMPTS:
                logger.debug(f"waiting for route to finish, {attempt} seconds elapsed")
                time.sleep(1)
                attempt += 1
                if not currently_running.get(route_variables, False):
                    logger.debug(
                        f"route finished after {attempt} seconds, returning cached response"
                    )
                    if route_variables in response:
                        return response[route_variables]
                    else:
                        logger.warning("route finished, but response not in cache")
                        break

        # 1.1 check if its been called before and not currently running
        if (route_variables not in last_updated) and (
            not currently_running.get(route_variables, False)
        ):
            logger.debug("First time this is route run, and not running now")

            # run the route
            currently_running[route_variables] = True
            response[route_variables] = func(*args, **kwargs)
            currently_running[route_variables] = False
            last_updated[route_variables] = datetime.now(tz=timezone.utc)

            return response[route_variables]

        # 1.2 rerun if cache time out is up and not currently running
        now = datetime.now(tz=timezone.utc)
        if now - timedelta(seconds=cache_time_seconds) > last_updated[route_variables] and (
            not currently_running.get(route_variables, False)
        ):
            logger.debug(
                f"Not using cache as longer than {cache_time_seconds} seconds, and not running now"
            )

            # run the route
            currently_running[route_variables] = True
            response[route_variables] = func(*args, **kwargs)
            currently_running[route_variables] = False
            last_updated[route_variables] = now

            return response[route_variables]

        # 1.3. re-run if response is not cached for some reason or is empty
        if route_variables not in response or response[route_variables] is None:
            logger.debug("not using cache as response is empty")
            attempt = 0
            # wait until response has been cached
            while attempt < N_ATTEMPTS:
                logger.debug(f"waiting for response to be cached, {attempt} seconds elapsed")
                time.sleep(1)
                attempt += 1
                if route_variables in response and response[route_variables] is not None:
                    logger.debug(
                        f"response cached after {attempt} seconds, returning cached response"
                    )
                    break
            if attempt >= N_ATTEMPTS:
                # if response is not in cache after 10 seconds, re-run
                logger.debug("response not cached after 10 seconds, re-running")

                # run the route
                currently_running[route_variables] = True
                response[route_variables] = func(*args, **kwargs)
                currently_running[route_variables] = False
                last_updated[route_variables] = now

                return response[route_variables]

        # 1.4 use cache
        logger.debug(f"Using cache route, cache made at {last_updated[route_variables]}")
        return response[route_variables]

    return wrapper
