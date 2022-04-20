""" Authentical  objects """
import os

from fastapi_auth0 import Auth0

domain = os.getenv("AUTH0_DOMAIN")
api_audience = os.getenv("AUTH0_API_AUDIENCE")

auth = Auth0(domain=domain, api_audience=api_audience)
