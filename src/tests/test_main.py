""" Test for main app """
from fastapi.testclient import TestClient
from nowcasting_datamodel.fake import make_fake_forecasts, make_fake_national_forecast
from nowcasting_datamodel.models import Forecast, ManyForecasts

from database import get_session
from main import app, version

client = TestClient(app)


def test_read_main():
    """Check main route works"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == version
