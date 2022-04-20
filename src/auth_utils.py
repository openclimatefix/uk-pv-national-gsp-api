""" Authentical  objects """
import os

from fastapi_auth0 import Auth0

domain = os.getenv("AUTH0_DOMAIN", "not-set")
api_audience = os.getenv("AUTH0_API_AUDIENCE", "not-set")


def get_auth():
    """Make Auth0 object"""
    return Auth0(domain=domain, api_audience=api_audience)


def get_auth_implicit_scheme():
    """Get authentical implicit scheme - this can be mocked in tests"""
    auth = get_auth()

    return auth.implicit_scheme


def get_user():
    """Get user used for authentication - this function can be mocked for tests"""
    auth = get_auth()
    return auth.get_user
