"""v0_6_0_notifications

Adds notification_templates, escalation_policies, escalation_steps and
escalation_events tables for v0.6.0.

Revision ID: a1b2c3d4e5f6
Revises: 7f1b2c3d4e5f
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7f1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("severity_filter", sa.String(length=50), nullable=True),
        sa.Column("title_template", sa.String(length=500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "escalation_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "escalation_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("delay_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["escalation_policies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["notification_channels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_escalation_steps_policy_id"), "escalation_steps", ["policy_id"]
    )
    op.create_index(
        op.f("ix_escalation_steps_channel_id"), "escalation_steps", ["channel_id"]
    )

    op.create_table(
        "escalation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"], ["escalation_policies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["channel_id"], ["notification_channels.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_escalation_events_policy_id"), "escalation_events", ["policy_id"]
    )
    op.create_index(
        op.f("ix_escalation_events_alert_id"), "escalation_events", ["alert_id"]
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_escalation_events_alert_id"), table_name="escalation_events"
    )
    op.drop_index(
        op.f("ix_escalation_events_policy_id"), table_name="escalation_events"
    )
    op.drop_table("escalation_events")
    op.drop_index(
        op.f("ix_escalation_steps_channel_id"), table_name="escalation_steps"
    )
    op.drop_index(
        op.f("ix_escalation_steps_policy_id"), table_name="escalation_steps"
    )
    op.drop_table("escalation_steps")
    op.drop_table("escalation_policies")
    op.drop_table("notification_templates")
