import os
from functools import wraps
from datetime import datetime, timedelta


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
    response = None

    @wraps(func)
    async def wrapper(*args, **kwargs):
        nonlocal response
        nonlocal last_updated

        print(response)
        if not last_updated:
            last_updated = datetime.now()
            response = await func(*args, **kwargs)
            return response

        now = datetime.now()
        if now - timedelta(seconds=cache_time_seconds) > last_updated:
            last_updated = datetime.now()
            response = await func(*args, **kwargs)
            return response

        return response

    return wrapper
