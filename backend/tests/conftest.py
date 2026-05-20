import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.services.scheduler import get_scheduler


@pytest.fixture(autouse=True)
def clear_scheduler():
    yield
    for job in get_scheduler().get_jobs():
        job.remove()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncSession:
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


def _make_user(role: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role}@autoflowops.local",
        name=f"{role.capitalize()} User",
        password_hash="irrelevant",
        role=role,
        is_active=True,
    )


_FAKE_ADMIN = _make_user("admin")
_FAKE_OPERATOR = _make_user("operator")
_FAKE_VIEWER = _make_user("viewer")


def _make_async_client(db_session: AsyncSession, fake_user: User) -> AsyncClient:
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncClient:
    async with _make_async_client(db_session, _FAKE_ADMIN) as client:
        yield client
    app.dependency_overrides = {}


@pytest.fixture
async def operator_client(db_session: AsyncSession) -> AsyncClient:
    async with _make_async_client(db_session, _FAKE_OPERATOR) as client:
        yield client
    app.dependency_overrides = {}


@pytest.fixture
async def viewer_client(db_session: AsyncSession) -> AsyncClient:
    async with _make_async_client(db_session, _FAKE_VIEWER) as client:
        yield client
    app.dependency_overrides = {}
