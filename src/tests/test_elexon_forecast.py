from typing import Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from elexonpy.api.generation_forecast_api import GenerationForecastApi

from pydantic_models import BaseModel, SolarForecastResponse

API_URL = "/v0/solar/GB/national/elexon"


class MockClass(BaseModel):
    start_time: str
    quantity: float
    business_type: Optional[str] = "Solar generation"

    def to_dict(self):
        return self.__dict__


mock_data = [
    MockClass(
        **{
            "start_time": "2024-07-24T16:00:00+00:00",
            "quantity": 0,
        }
    ),
    MockClass(
        **{
            "start_time": "2024-07-24T16:30:00+00:00",
            "quantity": 0,
        }
    ),
]
mock_response = MagicMock()
mock_response.data = mock_data


@patch.object(GenerationForecastApi, "forecast_generation_wind_and_solar_day_ahead_get")
def test_get_elexon_forecast_mock(mock_function, api_client):
    # Set mock_response
    mock_function.return_value = mock_response

    # Call the API endpoint
    response = api_client.get(API_URL)
    print("Response Headers:", response.headers)
    # Assertions
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"

    api_data = response.json()["data"]
    assert len(api_data) == len(mock_data)
    for i in range(len(api_data)):
        assert api_data[i]["expected_power_generation_megawatts"] == mock_data[i].quantity
        assert pd.Timestamp(api_data[i]["timestamp"]) == pd.Timestamp(mock_data[i].start_time)


@pytest.mark.integration
def test_get_elexon_forecast(api_client):
    response = api_client.get(API_URL)

    # Assertions
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"

    solar_forecast = SolarForecastResponse(**response.json())

    assert len(solar_forecast.data) > 0
