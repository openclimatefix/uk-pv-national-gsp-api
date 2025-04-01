""" Main FastAPI app """

import logging
import os
import time
from datetime import timedelta

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse

# Custom routers
from gsp import router as gsp_router
from national import router as national_router
from pydantic_models import ModelName  # Corrected import position
from redoc_theme import get_redoc_html_with_theme
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from status import router as status_router
from system import router as system_router
from utils import limiter, traces_sampler

# flake8: noqa E501

# Structlog configuration
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(logging, os.getenv("LOGLEVEL", "INFO"))
    ),
    processors=[
        structlog.processors.EventRenamer("message", replace_by="_event"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        structlog.processors.dict_tracebacks,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.stdlib.get_logger()

folder = os.path.dirname(os.path.abspath(__file__))

title = "Quartz Solar API"
version = "1.5.77"

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENVIRONMENT", "local"),
    traces_sampler=traces_sampler,
)
sentry_sdk.set_tag("app_name", "quartz-solar-api")
sentry_sdk.set_tag("version", version)

# noqa: E501
description = """

## General Overview

As part of Open Climate Fix’s
[open source project](https://github.com/openclimatefix), the Quartz Solar API
offers access to solar energy forecasts for the UK.

__Nowcasting__ means __forecasting for the next few hours__.
OCF has built a predictive model that nowcasts solar energy generation for
the UK’s National Grid ESO (electricity system operator) and a few other test
users. National Grid balances the electricity grid across 317
[GSPs](https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points)
(grid supply points), which are regionally located throughout the country.
OCF's Quartz Solar App synthesizes real-time PV
data, numeric weather predictions (nwp), satellite imagery
(looking at cloud cover), as well as GSP data to
forecast how much solar energy will be generated for a given GSP.

## Key Terms and Sample Use Cases

### Key Terms

**Forecast**:
- Forecasts are produced in 30-minute time steps, projecting GSP yields out to
    eight hours ahead.
- The geographic extent of each forecast is all of Great Britain (GB).
- Forecasts are produced at the GB National and regional level (GSPs).

"""

app = FastAPI(docs_url="/swagger", redoc_url=None)

origins = os.getenv("ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time into response object header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = str(time.time() - start_time)
    logger.info(f"Process Time {process_time} {request.url}")
    response.headers["X-Process-Time"] = process_time

    return response


thirty_minutes = timedelta(minutes=30)

# Dependency
v0_route_solar = "/v0/solar/GB"
v0_route_system = "/v0/system/GB"
app.include_router(national_router, prefix=f"{v0_route_solar}/national")
app.include_router(gsp_router, prefix=f"{v0_route_solar}/gsp")
app.include_router(status_router, prefix=f"{v0_route_solar}")
app.include_router(system_router, prefix=f"{v0_route_system}/gsp")


@app.get("/v0/solar/GB/national/forecast", response_model=SolarForecastResponse)
def get_national_forecast(model_name: ModelName = ModelName.blend):
    """### Get National Forecast

    Returns the national solar forecast based on the selected model.
    """
    # Logic to handle the model selection
    if model_name == ModelName.blend:
        forecast_data = "Blend model forecast data"
    elif model_name == ModelName.pvnet_v2:
        forecast_data = "PVNet V2 forecast data"
    elif model_name == ModelName.pvnet_da:
        forecast_data = "PVNet DA forecast data"
    elif model_name == ModelName.pvnet_ecwmf:
        forecast_data = "PVNet ECMWF forecast data"

    return forecast_data


@app.get("/favicon.ico", include_in_schema=False)
def get_favicon() -> FileResponse:
    """Get favicon"""
    return FileResponse(f"{folder}/favicon.ico")


@app.get("/QUARTZSOLAR_LOGO_SECONDARY_BLACK_1.png", include_in_schema=False)
def get_nowcasting_logo() -> FileResponse:
    """Get logo"""
    return FileResponse(f"{folder}/QUARTZSOLAR_LOGO_SECONDARY_BLACK_1.png")


@app.get("/docs", include_in_schema=False)
def redoc_html():
    """### Render ReDoc with custom theme options included"""
    return get_redoc_html_with_theme(
        title=title,
    )


def custom_openapi():
    """Make custom redoc theme"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=title,
        version=version,
        description=description,
        contact={
            "name": "Nowcasting by Open Climate Fix",
            "url": "https://quartz.solar",
            "email": "info@openclimatefix.org",
        },
        license_info={
            "name": "MIT License",
            "url": "https://github.com/openclimatefix/nowcasting_api/blob/main/LICENSE",
        },
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {"url": "/QUARTZSOLAR_LOGO_SECONDARY_BLACK_1.png"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
