"""User management endpoint tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import hash_password


async def _seed_user(
    session: AsyncSession,
    email: str = "seed@test.com",
    role: str = "viewer",
) -> User:
    user = User(
        email=email,
        name="Seed User",
        password_hash=hash_password("pass"),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_admin_can_list_users(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/users")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_admin_can_create_user(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/users",
        json={
            "email": "new@test.com",
            "name": "New User",
            "password": "pass1234",
            "role": "viewer",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "viewer"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, email="dup@test.com")
    response = await async_client.post(
        "/api/users",
        json={"email": "dup@test.com", "name": "Dup", "password": "pw", "role": "viewer"},  # noqa: E501
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_admin_can_update_role(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _seed_user(db_session, email="role@test.com", role="viewer")
    response = await async_client.patch(
        f"/api/users/{user.id}", json={"role": "operator"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "operator"


@pytest.mark.asyncio
async def test_cannot_demote_last_active_admin(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _seed_user(db_session, email="only-admin@test.com", role="admin")
    response = await async_client.patch(
        f"/api/users/{admin.id}", json={"role": "operator"}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_can_demote_admin_when_another_active_admin_exists(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _seed_user(db_session, email="admin-a@test.com", role="admin")
    await _seed_user(db_session, email="admin-b@test.com", role="admin")
    response = await async_client.patch(
        f"/api/users/{admin.id}", json={"role": "operator"}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "operator"


@pytest.mark.asyncio
async def test_create_user_invalid_role(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/users",
        json={
            "email": "bad@test.com",
            "name": "Bad",
            "password": "pw",
            "role": "superuser",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_can_reset_password(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await _seed_user(db_session, email="reset@test.com")
    response = await async_client.post(
        f"/api/users/{user.id}/reset-password",
        json={"new_password": "newpassword123"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_operator_cannot_list_users(operator_client: AsyncClient) -> None:
    response = await operator_client.get("/api/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_list_users(viewer_client: AsyncClient) -> None:
    response = await viewer_client.get("/api/users")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_user_read_does_not_expose_password_hash(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_user(db_session, email="nohash@test.com")
    response = await async_client.get("/api/users")
    assert response.status_code == 200
    for user in response.json():
        assert "password_hash" not in user
        assert "password" not in user
