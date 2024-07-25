import pytest
import requests
import requests_mock

API_URL = "/v0/solar/GB/national/elexon"


@pytest.fixture
def mock_data():
    return {
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


def test_get_elexon_forecast_with_data(mock_data):
    with requests_mock.Mocker() as m:
        url = (
            f"{API_URL}?start_datetime_utc=2024-07-22T10:56:59.194610"
            f"&end_datetime_utc=2024-07-28T10:56:59.194680"
            f"&process_type=Day Ahead"
        )
        m.get(url, json=mock_data, headers={"Content-Type": "application/json"})

        response = requests.get(url)
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
