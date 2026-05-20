import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    message: str
    severity: str
    source_type: str | None
    source_id: uuid.UUID | None
    status: str
    created_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
