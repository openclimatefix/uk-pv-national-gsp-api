""" Test for main app """

from freezegun import freeze_time

from nowcasting_api.national import is_fake
from nowcasting_api.pydantic_models import NationalForecastValue, NationalYield


def test_is_fake_national_all_available_forecasts(monkeypatch, api_client):
    """Test FAKE environment for all GSPs are populating
    with fake data.
    """

    monkeypatch.setenv("FAKE", "1")
    assert is_fake() == 1
    # Connect to DB endpoint
    response = api_client.get("/v0/solar/GB/national/forecast")
    assert response.status_code == 200

    national_forecast_values = [NationalForecastValue(**f) for f in response.json()]
    assert national_forecast_values is not None

    # Disable is_fake environment
    monkeypatch.setenv("FAKE", "0")


# The freeze time is needed so the cahce doesnt interact with the test in test_national.py
# Ideally we would not have this
@freeze_time("2021-12-01")
def test_is_fake_national_get_truths_for_all_gsps(monkeypatch, api_client):
    """Test FAKE environment for all GSPs for yesterday and today
    are populating with fake data.
    """

    monkeypatch.setenv("FAKE", "1")
    assert is_fake() == 1
    # Connect to DB endpoint
    response = api_client.get("/v0/solar/GB/national/pvlive/")
    assert response.status_code == 200

    print(response.json())

    national_forecast_values = [NationalYield(**f) for f in response.json()]
    assert national_forecast_values is not None

    # Disable is_fake environment
    monkeypatch.setenv("FAKE", "0")
