from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_missing_auth_header():
    # Expect 403 Forbidden when hitting the endpoint without a token
    response = client.post("/v1/admit", json={
        "endpoint_path": "/api/v1/test",
        "method": "GET",
        "client_ip": "10.0.0.1"
    })
    assert response.status_code == 403

def test_healthz():
    # If there's a health endpoint, it should return 200
    # For now, we can test that the root or an invalid endpoint returns 404
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404
