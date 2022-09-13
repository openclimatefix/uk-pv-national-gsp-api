""" Test for main app """
from fastapi.testclient import TestClient

from main.py import app, version

client = TestClient(app)


def test_read_main():
    """Check main route works"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == version
