""" Main FastAPI app """
import logging
import os
import time
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from gsp import router as gsp_router
from status import router as status_router

# from pv import router as pv_router
logging.basicConfig(
    level=getattr(logging, os.getenv("LOGLEVEL", "DEBUG")),
    format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

version = "0.2.22"
description = """
As part of Open Climate Fix’s [open source project](https://github.com/openclimatefix), the 
Nowcasting API is still under development.

#### General Overview

__Nowcasting__ essentially means __forecasting for the next few hours__.
OCF has built a predictive model that nowcasts solar photovoltaic (PV) energy input for 
the UK’s National Grid ESO (electricity system operator). National Grid runs more than 
300 grid supply points (GSP’s), which are regionally located throughout the country. 
Every 30 minutes at the level of the GSP, OCF's Nowcasting App synthesizes live PV data, 
numeric weather predictions (nwp), satellite data (looking at cloud cover), as well as GSP 
data to create a forecast for how many megawatts of PV energy will likely be generated
at a given GSP. These incredibly accurate, short-term forecasts allow National Grid to 
reduce the amount of spinning reserves they need to run, ultimately reducing carbon emmisions.

In order to get started with reading the API’s forecast objects, it might be helpful to 
know that GSP's are referenced in the following ways:  gspId (ex. 122); gspName (ex. FIDF_1); 
regionName (ex. Fiddlers Ferry). The API provides information on when input data was last updated 
as well as a specific GSP's installed PV megawatt capacity.

You'll find more detailed information for each route in the documentation below.

If you have any questions, please don't hesitate to get in touch. 
And if you're interested in contributing to our open source project feel free to join us!
"""
app = FastAPI(
    title="Nowcasting API",
    version=version,
    description=description,
    contact={
        "name": "Open Climate Fix",
        "url": "https://openclimatefix.org",
        "email": "info@openclimatefix.org",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/openclimatefix/nowcasting_api/blob/main/LICENSE",
    },
)

origins = os.getenv("ORIGINS", "https://app.nowcasting.io").split(",")
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
    logger.debug(f"Process Time {process_time}")
    response.headers["X-Process-Time"] = process_time
    return response


thirty_minutes = timedelta(minutes=30)


# Dependency
v0_route = "/v0/GB/solar"


app.include_router(gsp_router, prefix=f"{v0_route}/gsp")
app.include_router(status_router, prefix=f"{v0_route}")
# app.include_router(pv_router, prefix=f"{v0_route}/pv")


@app.get("/")
async def get_api_information():
    """### Get basic information about the Nowcasting API

    This returns an object containing the basic information about the Nowcasting API.

    #### Metadata
    - title
    - version
    - description
    - documentation

    """

    logger.info("Route / has be called")

    return {
        "title": "Nowcasting API",
        "version": version,
        "description": description,
        "documentation": "https://api.nowcasting.io/docs",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon() -> FileResponse:
    """Get favicon"""
    return FileResponse("src/favicon.ico")
