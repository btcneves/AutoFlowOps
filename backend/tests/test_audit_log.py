"""Audit log generation and masking tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.auth import hash_password


async def _create_user_in_db(
    session: AsyncSession,
    email: str = "u@test.com",
    password: str = "secret",
    role: str = "admin",
) -> User:
    user = User(
        email=email,
        name="Test",
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_success_creates_audit_log(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user_in_db(db_session, email="login@test.com", password="pw123")
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "login@test.com", "password": "pw123"},
    )
    assert response.status_code == 200
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "auth.login_success")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1


@pytest.mark.asyncio
async def test_login_failure_creates_audit_log(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "wrong"},
    )
    assert response.status_code == 401
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "auth.login_failure")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].status == "failure"


@pytest.mark.asyncio
async def test_job_create_creates_audit_log(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await async_client.post(
        "/api/jobs",
        json={
            "name": "Audit test job",
            "method": "GET",
            "url": "https://example.com",
            "schedule_type": "manual",
        },
    )
    assert response.status_code == 201
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "jobs.create")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    assert logs[0].resource_type == "job"


@pytest.mark.asyncio
async def test_audit_log_metadata_does_not_contain_password(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user_in_db(db_session, email="masked@test.com", password="secret123")
    await async_client.post(
        "/api/auth/login",
        json={"email": "masked@test.com", "password": "secret123"},
    )
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == "auth.login_success")
    )
    for log in result.scalars().all():
        meta = log.metadata_ or {}
        assert "secret123" not in str(meta)
        assert "password" not in str(meta).lower() or "***" in str(meta)


@pytest.mark.asyncio
async def test_audit_log_filter_by_action(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user_in_db(db_session, email="filter@test.com", password="pw")
    await async_client.post(
        "/api/auth/login",
        json={"email": "filter@test.com", "password": "pw"},
    )
    response = await async_client.get(
        "/api/audit-logs", params={"action": "auth.login_success"}
    )
    assert response.status_code == 200
    data = response.json()
    assert all(entry["action"] == "auth.login_success" for entry in data)
