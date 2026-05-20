from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "AutoFlowOps"
    assert "env" in data
    assert data["database"] == "ok"


def test_version_returns_version(client: TestClient) -> None:
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["app"] == "AutoFlowOps"
    assert data["version"] != ""
