import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import create_access_token, hash_password


async def _create_user(
    session: AsyncSession,
    email: str = "user@test.com",
    password: str = "secret",
) -> User:
    user = User(
        email=email,
        name="Test User",
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, db_session: AsyncSession):
    await _create_user(db_session)
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(
    async_client: AsyncClient, db_session: AsyncSession
):
    await _create_user(db_session)
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "wrong"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(async_client: AsyncClient):
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "anything"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(async_client: AsyncClient, db_session: AsyncSession):
    from app.database import get_db
    from app.dependencies import get_current_user
    from app.main import app

    user = await _create_user(db_session, email="me@test.com")
    token = create_access_token(str(user.id), user.role)

    saved_overrides = app.dependency_overrides.copy()
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    try:
        async def override_db():
            yield db_session

        app.dependency_overrides[get_db] = override_db
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@test.com"
    finally:
        app.dependency_overrides = saved_overrides


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(db_session: AsyncSession):
    from httpx import ASGITransport
    from httpx import AsyncClient as HClient

    from app.database import get_db
    from app.main import app

    async def override_db():
        yield db_session

    original = app.dependency_overrides.copy()
    app.dependency_overrides = {get_db: override_db}
    try:
        async with HClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/jobs")
            assert response.status_code == 401
    finally:
        app.dependency_overrides = original
