"""Caching utils for api using fastapi-cache"""

import os
from typing import Any, Callable, Optional

import structlog
from database import save_api_call_to_db
from fastapi import Request
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

logger = structlog.stdlib.get_logger()

# Configuration constants with environment variable fallbacks
CACHE_TIME_SECONDS = int(os.getenv("CACHE_TIME_SECONDS", 120))
DELETE_CACHE_TIME_SECONDS = int(os.getenv("DELETE_CACHE_TIME_SECONDS", 240))


def setup_cache():
    """Initialize the FastAPICache with an in-memory backend.

    Call this function in main.py after creating the FastAPI app.

    Example:
    ```
    app = FastAPI()

    @app.on_event("startup")
    async def startup():
        setup_cache()
    ```
    """
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    logger.info("FastAPI Cache initialized with InMemoryBackend")


def generate_cache_key(func: Callable, request: Request, *args, **kwargs) -> str:
    """
    Generate a unique cache key based on the endpoint path and query parameters.

    :param func: The route handler function
    :param request: The FastAPI request object
    :return: A string to be used as cache key
    """
    # Create key from path and sorted query params
    path = request.url.path
    query_params = sorted(request.query_params.items())
    key = f"{path}:{query_params}"
    logger.debug(f"Generated cache key: {key}")
    return key


def save_api_call(
    request: Request = None, user: Optional[Any] = None, session: Optional[Any] = None
):
    """
    Save API call to database.

    This can be used as a dependency in FastAPI routes.

    :param request: The FastAPI request object
    :param user: The user making the request, if authenticated
    :param session: The database session
    """
    save_api_call_to_db(session=session, user=user, request=request)
    return request


def cache_response(expiration: int = CACHE_TIME_SECONDS):
    """
    Decorator that caches the response of a FastAPI function.

    Example:
    ```
    @app.get("/")
    @cached_response()
    async def example(request: Request = Depends(save_api_call)):
        return {"message": "Hello World"}
    ```

    :param expiration: Cache expiration time in seconds
    :return: Decorated function with caching
    """

    def decorator(func: Callable):
        return cache(expire=expiration, namespace="api", key_builder=generate_cache_key)(func)

    return decorator
