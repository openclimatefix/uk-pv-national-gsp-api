""" Authentical  objects """
import os

from fastapi_auth0 import Auth0

domain = os.getenv("AUTH0_DOMAIN", "not-set")
api_audience = os.getenv("AUTH0_API_AUDIENCE", "not-set")

auth = None


def get_auth_implicit_scheme():
    """Get authentical implicit scheme - this can be mocked in tests"""
    auth = Auth0(domain=domain, api_audience=api_audience)

    return auth.implicit_scheme


def get_user():
    """Get user used for authentication

    This function can be mocked for tests"""
    return auth.get_user
