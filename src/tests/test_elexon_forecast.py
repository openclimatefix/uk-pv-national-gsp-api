import pytest
import requests
import requests_mock

API_URL = "/v0/solar/GB/national/elexon"


@pytest.fixture
def mock_data():
    return {
        "data": [
            {
                "timestamp": "2024-07-24T16:45:09+00:00",
                "expected_power_generation_megawatts": 0,
                "plevels": None,
            },
            {
                "timestamp": "2024-07-24T16:45:09+00:00",
                "expected_power_generation_megawatts": 0,
                "plevels": None,
            },
        ]
    }


def test_get_elexon_forecast_with_data(mock_data, api_client):
    with requests_mock.Mocker() as m:
        url = (
            f"https://data.elexon.co.uk/bmrs/api/v1/forecast/generation/wind-and-solar/day-ahead"
        )
        m.get(url, json=mock_data, headers={"Content-Type": "application/json"})

        response = api_client.get('/v0/solar/GB/national/elexon')
        print("Response Headers:", response.headers)
        # Assertions
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/json"
        assert response.json() == mock_data


@pytest.fixture
def empty_mock_data():
    return {"data": []}


def test_get_elexon_forecast_no_data(empty_mock_data):
    with requests_mock.Mocker() as m:
        url = (
            f"{API_URL}?start_datetime_utc=2024-07-22T10:56:59.194610"
            f"&end_datetime_utc=2024-07-28T10:56:59.194680"
            f"&process_type=Day Ahead"
        )

        m.get(url, json=empty_mock_data, headers={"Content-Type": "application/json"})

        response = requests.get(url)
        print("Response Headers:", response.headers)
        # Assertions
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/json"
        assert response.json() == empty_mock_data
