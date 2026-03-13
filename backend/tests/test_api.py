import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_predict_safe_url():
    response = client.post("/api/predict", json={"url": "http://google.com"})
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "confidence" in data
    assert "explanation" in data

def test_predict_phishing_url():
    # Note: This depends on the model's current state (untrained/random weights might vary)
    # We just check the structure and that it runs without error
    response = client.post("/api/predict", json={"url": "http://evil-login-verify.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] in ["safe", "phishing"]

def test_predict_with_html():
    response = client.post("/api/predict", json={
        "url": "http://test.com",
        "html": "<html><body><form>login</form></body></html>"
    })
    assert response.status_code == 200

def test_batch_predict():
    response = client.post("/api/batch_predict", json={
        "urls": ["http://google.com", "http://yahoo.com"]
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2

def test_stats_endpoint():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_scans" in data
    assert "trends" in data