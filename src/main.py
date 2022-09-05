""" Main FastAPI app """
import logging
import os
import time
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from routes.forecast import router as forecast_router
from routes.gsp import router as gsp_router
from routes.pvlive import router as pvlive_router
from routes.status import router as status_router

# from pv import router as pv_router
logging.basicConfig(
    level=getattr(logging, os.getenv("LOGLEVEL", "DEBUG")),
    format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

version = "0.2.21"
description = """
The Nowcasting API is still under development.
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

app.include_router(forecast_router, prefix=f"{v0_route}/forecast")
app.include_router(pvlive_router, prefix=f"{v0_route}/pvlive")
app.include_router(gsp_router, prefix=f"{v0_route}/gsp")
app.include_router(status_router, prefix=f"{v0_route}")
# app.include_router(pv_router, prefix=f"{v0_route}/pv")


@app.get("/")
async def get_api_information():
    """Get information about the API itself"""

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
