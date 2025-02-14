""" Caching utils for api"""

import os
from functools import wraps
from fastapi import Request
from fastapi.responses import Response

import structlog

from database import save_api_call_to_db

logger = structlog.stdlib.get_logger()

CACHE_TIME_SECONDS = 120
cache_seconds = int(os.getenv("CACHE_TIME_SECONDS", CACHE_TIME_SECONDS))


def save_to_database(func):
    """
    Decorator that save teh api call to the database

    Example:
    ```
        app = FastAPI()

        @app.get("/")
        @save_to_database
        async def example():
            return {"message": "Hello World"}
    ```

    kwargs

    """
    @wraps(func)
    def wrapper(*args, **kwargs):  # noqa

        pass

        return func(*args, **kwargs)

    return wrapper


def request_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
):


    # get the variables that go into the route
    # we don't want to use the cache for different variables
    route_variables = kwargs['kwargs']

    # save route variables to db
    session = route_variables.get("session", None)
    user = route_variables.get("user", None)
    if session is not None:
        save_api_call_to_db(session=session, user=user, request=request)

    return ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])
