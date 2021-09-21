from fastapi.testclient import TestClient

from main import app, version, MultipleGSP

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()['version'] == version


def test_read_latest():
    response = client.get("/latest")
    assert response.status_code == 200

    r = MultipleGSP(**response.json())
    assert len(r.gsps) == 339
