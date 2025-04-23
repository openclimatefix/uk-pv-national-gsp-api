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
from gsp import router as gsp_router
from national import router as national_router
from redoc_theme import get_redoc_html_with_theme
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from status import router as status_router
from system import router as system_router
from utils import limiter, traces_sampler

# flake8: noqa E501

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
version = "1.5.85"

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
offers acces to solar energy forecasts for the UK.

__Nowcasting__ means __forecasting for the next few hours__.
OCF has built a predictive model that nowcasts solar energy generation for
the UK’s National Grid ESO (electricity system operator) and a few other test
users. National Grid
balances the electricity grid across 317
[GSPs](https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points)
(grid supply points), which are regionally located throughout the country.
OCF's Quartz Solar App synthesizes real-time PV
data, numeric weather predictions (nwp), satellite imagery
(looking at cloud cover), as well as GSP data to
forecast how much solar energy will generated for a given GSP.

OCF's incredibly accurate, short-term forecasts allow National Grid to reduce
the amount of spinning reserves they need to run at any given moment,
ultimately reducing carbon emmisions.

You’ll find an explanation of the terms we use and how solar forecasts are
defined in the **Key Terms and Sample Use Cases** section.

Predicatably, you'll find more detailed information for each API route in
the documentation below.

Quartz Solar API is built with [FastAPI](https://fastapi.tiangolo.com/), and
you can access the Swagger UI version at `/swagger`.

And if you're interested in contributing to our open source project, you can
get started by going to our [OCF Github](https://github.com/openclimatefix)
page and checking out our
“[list of good first issues](https://github.com/search?l=&p=1&q=user%3Aopenclimatefix+label%3A%22good+first+issue%22&ref=advsearch&type=Issues&utf8=%E2%9C%93&state=open)”!

You can find more information about the Quartz Solar app and view screenshots
of the UI on our [Notion page](https://openclimatefix.notion.site/Nowcasting-Documentation-0d718915650e4f098470d695aa3494bf).

If you have any further questions, please don't hesitate to get in touch.

## A Note on PV_Live

[PV_Live](https://www.solar.sheffield.ac.uk/pvlive/) is Sheffield
Solar’s API that provides estimate and truth PV generation values
by GSP.
In the Quartz Solar app, PV_Live Estimate and PV_Live Actual readings are
plotted on the same chart as the Quartz Solar forecast values, providing a
comparison.

The Quartz Solar forecast is trying to predict the PV_Live next-day updated
truth value.

The PV_Live API route that OCF uses has a parameter, _regime_, that's worth
explaining. _Regime_ can be set to _in-day_ or _day-after_. Basically,
_in-day_ values are the PV_Live. Estimate generation values. _Day-after_
values are the PV_Live Actual or truth
values updated the next day.

## Key Terms and Sample Use Cases

### Key Terms

**Forecast**:
- Forecasts are produced in 30-minute time steps, projecting GSP yields out to
    eight hours ahead.
- The geographic extent of each forecast is all of Great Britain (GB).
- Forecasts are produced at the GB National and regional level (GSPs).

**GSP (grid supply point):** GSPs supply the Great Britain transmission
network. The  Nowcasting map displays all 316 GSPs using their
geospatial boundaries.

**Gigawatt (GW):** A gigawatt is equal to 1,000 megawatts and is  a unit of
power used to describe electrical power production. The UK has a solar
generation capacity of around 14 GW.

**MW (megawatt):** A megawatt is a unit of power used to describe electrical
power production. At the GSP level, for example, solar power production is
measured in MW. This is not to be confused with MWh (megawatt hour), which is
a unit of energy equivalent to a steady power of one megawatt running for
one hour.

**Normalization:** A value is said to be ***normalized*** when rendered as a
percentage of a total value. In the Quartz Solar UI’s case, this means PV
actual values or PV forecasted values can be presented as a percentage of
total installed PV generation capacity. A user might find normalized values
meaningful when comparing forecasted and actual PV generation between GSPs
with different installed PV capacities.

**PV_Live:** [PV_Live](https://www.solar.sheffield.ac.uk/pvlive/) is Sheffield
Solar’s API that reports estimate PV data for each GSP and then updated truth
values for the following day. These readings are updated throughout the day,
reporting the actual or *truth* values the following day by late morning UTC.
In the Quartz Solar UI, PV_Live’s estimate and updated truth values on both
the national and GSP level are plotted alongside the Quartz Solar forecast
values.

### Sample Use Cases

Here a few use cases for of the Quartz Solar API routes.

*I, the user, would like to fetch…*

- Data on the OCF national forecast as many hours into the future as available.
    - **Get National Forecast**
   ```https://api.quartz.solar/v0/solar/GB/national/forecast```

- Great Britain's PV generation truth value for yesterday generated by PV_Live.
    - **Get National Pvlive**
    ```https://api.quartz.solar/v0/solar/GB/national/pvlive```

"""
app = FastAPI(docs_url="/swagger", redoc_url=None)

# origins = os.getenv("ORIGINS",
# "https://*.nowcasting.io,
# https://*-openclimatefix.vercel.app,https://*.quartz.solar")
# .split(
#     ","
# )
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
# app.include_router(pv_router, prefix=f"{v0_route}/pv")


@app.get("/")
def get_api_information():
    """### Get basic Quartz Solar API information

    Returns a json object with basic information about the Quartz Solar API.

    """

    logger.info("Route / has be called")

    return {
        "title": "Quartz Solar API",
        "version": version,
        "description": description,
        "documentation": "https://api.quartz.solar/docs",
        "swagger ui": "https://api.quartz.solar/swagger",
    }


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


# OpenAPI (ReDoc) custom theme
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
