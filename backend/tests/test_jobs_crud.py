"""Integration tests for /api/jobs CRUD endpoints."""

from httpx import AsyncClient

_JOB_PAYLOAD = {
    "name": "Test Job",
    "url": "http://example.com/api",
    "method": "GET",
}


async def test_create_job_returns_201(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/jobs", json=_JOB_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Job"
    assert data["url"] == "http://example.com/api"
    assert data["method"] == "GET"
    assert data["type"] == "http"
    assert data["status"] == "active"
    assert "id" in data


async def test_create_job_headers_are_masked(async_client: AsyncClient) -> None:
    payload = {
        **_JOB_PAYLOAD,
        "name": "Job With Auth",
        "headers": {
            "Authorization": "Bearer secret",
            "Content-Type": "application/json",
        },
    }
    response = await async_client.post("/api/jobs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["headers_masked"]["Authorization"] == "***"
    assert data["headers_masked"]["Content-Type"] == "application/json"


async def test_list_jobs_returns_created(async_client: AsyncClient) -> None:
    create = await async_client.post(
        "/api/jobs", json={**_JOB_PAYLOAD, "name": "List Me"}
    )
    assert create.status_code == 201

    response = await async_client.get("/api/jobs")
    assert response.status_code == 200
    names = [j["name"] for j in response.json()]
    assert "List Me" in names


async def test_get_job_returns_detail(async_client: AsyncClient) -> None:
    create = await async_client.post("/api/jobs", json=_JOB_PAYLOAD)
    job_id = create.json()["id"]

    response = await async_client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id


async def test_get_job_not_found(async_client: AsyncClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.get(f"/api/jobs/{fake_id}")
    assert response.status_code == 404


async def test_update_job_name(async_client: AsyncClient) -> None:
    create = await async_client.post("/api/jobs", json=_JOB_PAYLOAD)
    job_id = create.json()["id"]

    response = await async_client.patch(
        f"/api/jobs/{job_id}", json={"name": "Updated Name"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["url"] == _JOB_PAYLOAD["url"]


async def test_update_job_status_pause(async_client: AsyncClient) -> None:
    create = await async_client.post("/api/jobs", json=_JOB_PAYLOAD)
    job_id = create.json()["id"]

    response = await async_client.patch(
        f"/api/jobs/{job_id}", json={"status": "paused"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paused"


async def test_update_job_not_found(async_client: AsyncClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.patch(f"/api/jobs/{fake_id}", json={"name": "x"})
    assert response.status_code == 404


async def test_delete_job(async_client: AsyncClient) -> None:
    create = await async_client.post("/api/jobs", json=_JOB_PAYLOAD)
    job_id = create.json()["id"]

    response = await async_client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 204

    check = await async_client.get(f"/api/jobs/{job_id}")
    assert check.status_code == 404


async def test_delete_job_not_found(async_client: AsyncClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.delete(f"/api/jobs/{fake_id}")
    assert response.status_code == 404


async def test_create_job_validation_error(async_client: AsyncClient) -> None:
    response = await async_client.post("/api/jobs", json={"name": "", "url": ""})
    assert response.status_code == 422
