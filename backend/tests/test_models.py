"""Verifies model imports, table names, columns, and basic DB round-trip."""

import uuid

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import (
    Alert,
    AuditLog,
    Base,
    Execution,
    Job,
    NotificationChannel,
    NotificationDelivery,
    Report,
    User,
    Webhook,
    WebhookEvent,
)


@pytest.fixture(scope="module")
async def sqlite_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


def test_user_table_name():
    assert User.__tablename__ == "users"


def test_job_table_name():
    assert Job.__tablename__ == "jobs"


def test_execution_table_name():
    assert Execution.__tablename__ == "executions"


def test_webhook_table_name():
    assert Webhook.__tablename__ == "webhooks"


def test_webhook_event_table_name():
    assert WebhookEvent.__tablename__ == "webhook_events"


def test_alert_table_name():
    assert Alert.__tablename__ == "alerts"


def test_report_table_name():
    assert Report.__tablename__ == "reports"


def test_notification_channel_table_name():
    assert NotificationChannel.__tablename__ == "notification_channels"


def test_notification_delivery_table_name():
    assert NotificationDelivery.__tablename__ == "notification_deliveries"


def test_audit_log_table_name():
    assert AuditLog.__tablename__ == "audit_logs"


def test_all_tables_registered():
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users",
        "jobs",
        "executions",
        "webhooks",
        "webhook_events",
        "alerts",
        "reports",
        "notification_channels",
        "notification_deliveries",
        "notification_templates",
        "escalation_policies",
        "escalation_steps",
        "escalation_events",
        "audit_logs",
    }
    assert expected == table_names


async def test_create_all_tables(sqlite_engine):
    async with sqlite_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: sa_inspect(sync_conn).get_table_names()
        )
    assert set(tables) == {
        "users",
        "jobs",
        "executions",
        "webhooks",
        "webhook_events",
        "alerts",
        "reports",
        "notification_channels",
        "notification_deliveries",
        "notification_templates",
        "escalation_policies",
        "escalation_steps",
        "escalation_events",
        "audit_logs",
    }


def test_job_has_required_columns():
    columns = {c.name for c in Job.__table__.columns}
    required = {
        "id",
        "name",
        "type",
        "status",
        "schedule_type",
        "timeout_seconds",
        "retry_count",
        "alert_on_failure",
        "created_at",
        "updated_at",
    }
    assert required.issubset(columns)


def test_execution_has_masking_columns():
    columns = {c.name for c in Execution.__table__.columns}
    assert "request_headers_masked" in columns
    assert "request_body_masked" in columns


def test_webhook_has_secret_token_hash():
    columns = {c.name for c in Webhook.__table__.columns}
    assert "secret_token_hash" in columns
    assert "slug" in columns


def test_audit_log_has_required_columns():
    columns = {c.name for c in AuditLog.__table__.columns}
    required = {
        "id", "user_id", "action", "resource_type", "resource_id",
        "status", "ip_address", "user_agent", "metadata", "created_at",
    }
    assert required.issubset(columns)


def test_user_has_last_login_at():
    columns = {c.name for c in User.__table__.columns}
    assert "last_login_at" in columns


def test_job_can_be_instantiated():
    job = Job(name="test", url="http://example.com")
    assert job.name == "test"
    assert job.url == "http://example.com"


def test_user_can_be_instantiated():
    user = User(email="a@b.com", name="Test", password_hash="x")
    assert user.email == "a@b.com"
    assert user.name == "Test"


async def test_uuid_primary_keys_after_db_roundtrip(sqlite_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            email="uuid_test@example.com",
            name="UUID Test",
            password_hash="hashed",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    assert isinstance(user.id, uuid.UUID)
