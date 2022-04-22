""" Authentical  objects """
import logging
import os

from fastapi_auth0 import Auth0

domain = os.getenv("AUTH0_DOMAIN", "not-set")
api_audience = os.getenv("AUTH0_API_AUDIENCE", "not-set")

logger = logging.getLogger(__name__)


def get_auth():
    """Make Auth0 object

    If AUTH0_DOMAIN or AUTH0_API_AUDIENCE has been set, None is returned.
    This is useful for testing
    """
    if domain == "not-set" or api_audience == "notset":
        logger.warning('"AUTH0_DOMAIN" and "AUTH0_API_AUDIENCE" need to be set ')
        return None
    return Auth0(
        domain=domain,
        api_audience=api_audience,
        scopes={"read:pv": "Read PV data", "read:gsp": "Read GSP forecasts and truths"},
    )


def get_auth_implicit_scheme():
    """Get authentical implicit scheme - this can be mocked in tests

    If AUTH0_DOMAIN or AUTH0_API_AUDIENCE has been set, a empty None is returned.
    This is useful for testing
    """
    auth = get_auth()

    if auth is None:
        return lambda: None

    return auth.implicit_scheme


def get_user():
    """Get user used for authentication - this function can be mocked for tests

    If AUTH0_DOMAIN or AUTH0_API_AUDIENCE has been set, a empty None is returned.
    This is useful for testing
    """
    auth = get_auth()

    if auth is None:
        return lambda: None

    return auth.get_user
