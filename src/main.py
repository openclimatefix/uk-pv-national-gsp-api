""" Main FastAPI app """
import logging
from datetime import timedelta

from fastapi import FastAPI

from dummy import create_dummy_national_forecast, create_dummy_gsp_forecast
from models import Forecast, ManyForecasts

logger = logging.getLogger(__name__)

version = "0.1.5"
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

thirty_minutes = timedelta(minutes=30)


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
async def get_forecasts_for_a_specific_gsp(gsp_id) -> Forecast:
    """Get one forecast for a specific GSP id"""

    logger.info(f"Get forecasts for gsp id {gsp_id}")

    return create_dummy_gsp_forecast(gsp_id=gsp_id)


@app.get("/v0/forecasts/GB/pv/gsp", response_model=ManyForecasts)
async def get_all_available_forecasts() -> ManyForecasts:
    """Get the latest information for all available forecasts"""

    logger.info("Get forecasts for all gsps")

    return ManyForecasts(forecasts=[create_dummy_gsp_forecast(gsp_id) for gsp_id in range(10)])


@app.get("/v0/forecasts/GB/pv/national", response_model=Forecast)
async def get_nationally_aggregated_forecasts() -> Forecast:
    """Get an aggregated forecast at the national level"""

    logger.debug("Get national forecasts")

    return create_dummy_national_forecast()
