""" Test for main app """
from main import version


def test_read_main(api_client):
    """Check main route works"""
    response = api_client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == version
