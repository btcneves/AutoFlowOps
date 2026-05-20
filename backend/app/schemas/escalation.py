import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EscalationStepCreate(BaseModel):
    channel_id: uuid.UUID
    step_order: int = Field(ge=0)
    delay_minutes: int = Field(ge=0)


class EscalationStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    step_order: int
    channel_id: uuid.UUID
    delay_minutes: int
    created_at: datetime


class EscalationPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_active: bool = True
    steps: list[EscalationStepCreate] = Field(default_factory=list)


class EscalationPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class EscalationPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    steps: list[EscalationStepRead] = Field(default_factory=list)


class EscalationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    policy_id: uuid.UUID
    alert_id: uuid.UUID
    step_order: int
    channel_id: uuid.UUID
    status: str
    scheduled_at: datetime
    dispatched_at: datetime | None
    created_at: datetime
