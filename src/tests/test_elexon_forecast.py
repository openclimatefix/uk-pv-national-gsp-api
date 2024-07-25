from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class MockForecastItem:
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def to_dict(self):
        return self.__dict__


mock_data = [
    MockForecastItem(
        publish_time="2024-07-24T16:45:09+00:00",
        process_type="Day ahead",
        business_type="Solar generation",
        psr_type="Solar",
        start_time="2024-07-25T23:30:00+00:00",
        settlement_date="2024-07-26",
        settlement_period=2,
        quantity=0,
    ),
    MockForecastItem(
        publish_time="2024-07-24T16:45:09+00:00",
        process_type="Day ahead",
        business_type="Solar generation",
        psr_type="Solar",
        start_time="2024-07-25T23:00:00+00:00",
        settlement_date="2024-07-26",
        settlement_period=1,
        quantity=0,
    ),
]

# Define the full path for the patch target
PATCH_TARGET = (
    "elexonpy.api.generation_forecast_api."
    "GenerationForecastApi.forecast_generation_wind_and_solar_day_ahead_get"
)


def setup_mock_forecast(mock_forecast_api, data):
    mock_response = MagicMock()
    mock_response.data = data
    mock_forecast_api.return_value = mock_response


@patch(PATCH_TARGET)
def test_get_elexon_forecast_with_data(mock_forecast_api):
    setup_mock_forecast(mock_forecast_api, mock_data)
    endpoint = "/v0/solar/GB/national/elexon"
    params = {
        "start_datetime_utc": "2024-07-22T10:56:59.194610",
        "end_datetime_utc": "2024-07-28T10:56:59.194680",
        "process_type": "Day Ahead",
    }

    response = client.get(endpoint, params=params)

    expected_response = {
        "data": [
            {
                "publish_time": "2024-07-24T16:45:09+00:00",
                "process_type": "Day ahead",
                "business_type": "Solar generation",
                "psr_type": "Solar",
                "start_time": "2024-07-25T23:30:00+00:00",
                "settlement_date": "2024-07-26",
                "settlement_period": 2,
                "quantity": 0,
            },
            {
                "publish_time": "2024-07-24T16:45:09+00:00",
                "process_type": "Day ahead",
                "business_type": "Solar generation",
                "psr_type": "Solar",
                "start_time": "2024-07-25T23:00:00+00:00",
                "settlement_date": "2024-07-26",
                "settlement_period": 1,
                "quantity": 0,
            },
        ]
    }

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == expected_response


@patch(PATCH_TARGET)
def test_get_elexon_forecast_no_data(mock_forecast_api):
    setup_mock_forecast(mock_forecast_api, [])

    endpoint = "/v0/solar/GB/national/elexon"
    params = {
        "start_datetime_utc": "2024-07-22T10:56:59.194610",
        "end_datetime_utc": "2024-07-28T10:56:59.194680",
        "process_type": "Day Ahead",
    }
    response = client.get(endpoint, params=params)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == {"data": []}
