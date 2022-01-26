""" Main FastAPI app """
import logging
from datetime import timedelta

import geopandas as gpd
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nowcasting_forecast.database.models import Forecast, ManyForecasts
from sqlalchemy.orm.session import Session

from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_latest_national_forecast_from_database,
    get_session,
)
from gsp import get_gsp_boundaries_from_eso

logger = logging.getLogger(__name__)

version = "0.1.9"
description = """
The Nowcasting API is still under development. It only returns zeros for now.
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

origins = ["https://app.nowcasting.io"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

thirty_minutes = timedelta(minutes=30)


# Dependency


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


@app.get("/v0/forecasts/GB/pv/gsp/{gsp_id}", response_model=Forecast)
async def get_forecasts_for_a_specific_gsp(
    gsp_id, session: Session = Depends(get_session)
) -> Forecast:
    """Get one forecast for a specific GSP id"""

    logger.info(f"Get forecasts for gsp id {gsp_id}")

    return get_forecasts_for_a_specific_gsp_from_database(session=session, gsp_id=gsp_id)


@app.get("/v0/forecasts/GB/pv/gsp_boundaries")
async def get_gsp_boundaries() -> str:
    """Get one gsp boundary for a specific GSP id"""

    logger.info(f"Geting all GSP boundary")

    return get_gsp_boundaries_from_eso().to_json()


@app.get("/v0/forecasts/GB/pv/gsp", response_model=ManyForecasts)
async def get_all_available_forecasts(session: Session = Depends(get_session)) -> ManyForecasts:
    """Get the latest information for all available forecasts

    This is a wrapper around the dataset in
    'https://data.nationalgrideso.com/system/gis-boundaries-for-gb-grid-supply-points'
    """

    logger.info("Get forecasts for all gsps")

    return get_forecasts_from_database(session=session)


@app.get("/v0/forecasts/GB/pv/national", response_model=Forecast)
async def get_nationally_aggregated_forecasts(session: Session = Depends(get_session)) -> Forecast:
    """Get an aggregated forecast at the national level"""

    logger.debug("Get national forecasts")
    return get_latest_national_forecast_from_database(session=session)
