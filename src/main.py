""" Main FastAPI app """
import os
import time
from datetime import timedelta

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse

from gsp import router as gsp_router
from national import router as national_router
from redoc_theme import get_redoc_html_with_theme
from status import router as status_router
from system import router as system_router

structlog.configure(
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

title = "Nowcasting API"
version = "1.2.2"

description = """
As part of Open Climate Fix’s [open source project](https://github.com/openclimatefix), the
Nowcasting API is still under development.

#### General Overview

__Nowcasting__ essentially means __forecasting for the next few hours__.
OCF has built a predictive model that nowcasts solar energy generation for
the UK’s National Grid ESO (electricity system operator). National Grid runs more than
300
[GSPs](https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points)
(grid supply points), which are regionally located throughout the country.
OCF's Nowcasting App synthesizes real-time PV
data, numeric weather predictions (nwp), satellite imagery
(looking at cloud cover),
as well as GSP data to
forecast how much solar energy will generated for a given GSP.

Here are key aspects of the solar forecasts:
- Forecasts are produced in 30-minute time steps, projecting GSP yields out to
eight hours ahead.
- The geographic extent is all of Great Britain (GB).
- Forecasts are produced at the GB National and regional level (using GSPs).

OCF's incredibly accurate, short-term forecasts allow National Grid to reduce the amount of
spinning reserves they need to run at any given moment, ultimately reducing
carbon emmisions.

In order to get started with reading the API’s forecast objects, it might be helpful to
know that GSPs are referenced in the following ways:  gspId (ex. 122); gspName
(ex. FIDF_1); gspGroup (ex. )
regionName (ex. Fiddlers Ferry). The API provides information on when input data was
last updated as well as the installed photovoltaic (PV) megawatt capacity
(installedCapacityMw) of each individual GSP.

You'll find more detailed information for each route in the documentation below.

If you have any questions, please don't hesitate to get in touch.
And if you're interested in contributing to our open source project, feel free to join us!
"""
app = FastAPI(docs_url="/swagger", redoc_url=None)

# origins = os.getenv("ORIGINS", "https://*.nowcasting.io,https://*-openclimatefix.vercel.app")
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


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time into response object header"""
    start_time = time.time()
    response = await call_next(request)
    process_time = str(time.time() - start_time)
    logger.debug(f"Process Time {process_time} {call_next}")
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
    """### Get basic information about the Nowcasting API

    The object returned contains basic information about the Nowcasting API.

    """

    logger.info("Route / has be called")

    return {
        "title": "Nowcasting API",
        "version": version,
        "description": description,
        "documentation": "https://api.nowcasting.io/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
def get_favicon() -> FileResponse:
    """Get favicon"""
    return FileResponse(f"{folder}/favicon.ico")


@app.get("/nowcasting.png", include_in_schema=False)
def get_nowcasting_logo() -> FileResponse:
    """Get favicon"""
    return FileResponse(f"{folder}/nowcasting.png")


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
            "url": "https://nowcasting.io",
            "email": "info@openclimatefix.org",
        },
        license_info={
            "name": "MIT License",
            "url": "https://github.com/openclimatefix/nowcasting_api/blob/main/LICENSE",
        },
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {"url": "/nowcasting.png"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
