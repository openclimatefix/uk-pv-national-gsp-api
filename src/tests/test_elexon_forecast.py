from unittest.mock import patch

import pandas as pd

from pydantic_models import BaseModel
from typing import Optional

# InsightsApiModelsResponsesResponseWithMetadata1InsightsApiModelsResponsesTransparencyDayAheadGenerationForWindAndSolar

API_URL = "/v0/solar/GB/national/elexon"


class MockClass(BaseModel):

    publish_time: str
    quantity: float
    business_type: Optional[str] = "Solar generation"

    def to_dict(self):
        return self.__dict__


mock_data = [
    MockClass(
        **{
            "publish_time": "2024-07-24T16:45:09+00:00",
            "quantity": 0,
        }
    ),
    MockClass(
        **{
            "publish_time": "2024-07-24T16:45:09+00:00",
            "quantity": 0,
        }
    ),
]


class MockResponse:
    def __init__(self):
        self.data = mock_data


@patch("national.forecast_generation_wind_and_solar_day_ahead_get")
def test_get_elexon_forecast_with_data(mock_function, api_client):
    mock_function.return_value = MockResponse()

    response = api_client.get("/v0/solar/GB/national/elexon")
    print("Response Headers:", response.headers)
    # Assertions
    assert response.status_code == 200
    assert response.headers.get("Content-Type") == "application/json"

    api_data = response.json()["data"]
    assert len(api_data) == len(mock_data)
    for i in range(len(api_data)):
        assert api_data[i]["expected_power_generation_megawatts"] == mock_data[i].quantity
        assert pd.Timestamp(api_data[i]["timestamp"]) == pd.Timestamp(mock_data[i].publish_time)

