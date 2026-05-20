import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    # None means this template applies to all severities (catch-all)
    severity_filter: Mapped[str | None] = mapped_column(String(50))
    title_template: Mapped[str] = mapped_column(
        String(500), default="{title}"
    )
    body_template: Mapped[str] = mapped_column(
        Text,
        default=(
            "{title}\n\nSeverity: {severity}\n{message}"
        ),
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
