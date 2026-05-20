import uuid

from httpx import AsyncClient


async def test_list_workspaces_empty(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/workspaces")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_create_workspace(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/workspaces",
        json={"name": "Team Alpha", "slug": "team-alpha"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Team Alpha"
    assert data["slug"] == "team-alpha"
    assert data["is_default"] is False


async def test_create_workspace_duplicate_slug(async_client: AsyncClient) -> None:
    await async_client.post(
        "/api/workspaces", json={"name": "First", "slug": "my-slug"}
    )
    r = await async_client.post(
        "/api/workspaces", json={"name": "Second", "slug": "my-slug"}
    )
    assert r.status_code == 409


async def test_create_workspace_invalid_slug(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/workspaces", json={"name": "Bad", "slug": "Has Spaces!"}
    )
    assert r.status_code == 422


async def test_update_workspace(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/workspaces", json={"name": "Original", "slug": "original-ws"}
    )
    ws_id = created.json()["id"]
    r = await async_client.patch(f"/api/workspaces/{ws_id}", json={"name": "Renamed"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


async def test_delete_workspace(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/workspaces", json={"name": "Temporary", "slug": "temp-ws"}
    )
    ws_id = created.json()["id"]
    r = await async_client.delete(f"/api/workspaces/{ws_id}")
    assert r.status_code == 204


async def test_workspace_header_filters_jobs(
    async_client: AsyncClient,
) -> None:
    ws_r = await async_client.post(
        "/api/workspaces", json={"name": "Isolated", "slug": "isolated-ws"}
    )
    ws_id = ws_r.json()["id"]

    job_r = await async_client.post(
        "/api/jobs",
        json={
            "name": "WS Job",
            "method": "GET",
            "url": "http://example.com",
            "schedule_type": "manual",
        },
        headers={"X-Workspace-ID": ws_id},
    )
    assert job_r.status_code == 201

    filtered = await async_client.get(
        "/api/jobs", headers={"X-Workspace-ID": ws_id}
    )
    assert filtered.status_code == 200
    assert any(j["name"] == "WS Job" for j in filtered.json())

    other_ws = await async_client.post(
        "/api/workspaces", json={"name": "Other", "slug": "other-ws"}
    )
    other_id = other_ws.json()["id"]
    other_jobs = await async_client.get(
        "/api/jobs", headers={"X-Workspace-ID": other_id}
    )
    assert other_jobs.status_code == 200
    assert not any(j["name"] == "WS Job" for j in other_jobs.json())


async def test_workspace_not_found_returns_404(async_client: AsyncClient) -> None:
    r = await async_client.get(
        "/api/jobs",
        headers={"X-Workspace-ID": str(uuid.uuid4())},
    )
    assert r.status_code == 404


async def test_add_and_remove_member(async_client: AsyncClient) -> None:
    ws_r = await async_client.post(
        "/api/workspaces", json={"name": "Members WS", "slug": "members-ws"}
    )
    ws_id = ws_r.json()["id"]

    user_r = await async_client.post(
        "/api/users",
        json={
            "email": "member@test.local",
            "name": "Member User",
            "password": "password123",
            "role": "viewer",
        },
    )
    assert user_r.status_code == 201
    user_id = user_r.json()["id"]

    add_r = await async_client.post(
        f"/api/workspaces/{ws_id}/members",
        json={"user_id": user_id, "role": "member"},
    )
    assert add_r.status_code == 201

    members_r = await async_client.get(f"/api/workspaces/{ws_id}/members")
    assert members_r.status_code == 200
    assert any(m["user_id"] == user_id for m in members_r.json())

    del_r = await async_client.delete(f"/api/workspaces/{ws_id}/members/{user_id}")
    assert del_r.status_code == 204
