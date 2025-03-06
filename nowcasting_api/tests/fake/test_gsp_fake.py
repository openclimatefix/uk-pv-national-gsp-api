from nowcasting_datamodel.models import ForecastValue, LocationWithGSPYields, ManyForecasts

from gsp import GSP_TOTAL, is_fake


def test_is_fake_specific_gsp(monkeypatch, api_client, gsp_id=1):
    """### Test FAKE environment specific _gsp_id_ routes are populating
    with fake data.

    #### Parameters
    - **gsp_id**: Please set to any non-zero integer that is <= GSP_TOTAL
    """

    monkeypatch.setenv("FAKE", "1")
    assert is_fake() == 1

    # Specific _gsp_id_ route/endpoint for successful connection
    response = api_client.get(f"/v0/solar/GB/gsp/{gsp_id}/forecast")
    assert response.status_code == 200

    forecast_value = [ForecastValue(**f) for f in response.json()]
    assert forecast_value is not None

    # Disable is_fake environment
    monkeypatch.setenv("FAKE", "0")


def test_is_fake_get_truths_for_a_specific_gsp(monkeypatch, api_client, gsp_id=1):
    """### Test FAKE environment specific _gsp_id_ routes are populating
    with fake data.

    #### Parameters
    - **gsp_id**: Please set to any non-zero integer that is <= GSP_TOTAL
    """

    monkeypatch.setenv("FAKE", "1")
    assert is_fake() == 1

    # Specific _gsp_id_ route/endpoint for successful connection
    response = api_client.get(f"/v0/solar/GB/gsp/{gsp_id}/pvlive")
    assert response.status_code == 200

    forecast_value = [ForecastValue(**f) for f in response.json()]
    assert forecast_value is not None

    # Disable is_fake environment
    monkeypatch.setenv("FAKE", "0")


def test_is_fake_all_available_forecasts(monkeypatch, api_client):
    """Test FAKE environment for all GSPs are populating
    with fake data.
    """

    monkeypatch.setenv("FAKE", "1")
    assert is_fake() == 1

    # Connect to DB endpoint
    response = api_client.get("/v0/solar/GB/gsp/forecast/all/")
    assert response.status_code == 200

    all_forecasts = ManyForecasts(**response.json())
    assert all_forecasts is not None

    # Disable is_fake environment
    monkeypatch.setenv("FAKE", "0")


def test_is_fake_get_truths_for_all_gsps(
    monkeypatch, api_client, gsp_ids=list(range(1, GSP_TOTAL))
):
    """Test FAKE environment for all GSPs for yesterday and today
    are populating with fake data.
    """

    monkeypatch.setenv("FAKE", "1")
    assert is_fake() == 1

    # Connect to DB endpoint
    gsp_ids_str = ", ".join(map(str, gsp_ids))
    response = api_client.get(f"/v0/solar/GB/gsp/pvlive/all?gsp_ids={gsp_ids_str}")
    assert response.status_code == 200

    all_forecasts = [LocationWithGSPYields(**f) for f in response.json()]
    assert all_forecasts is not None

    # Disable is_fake environment
    monkeypatch.setenv("FAKE", "0")
