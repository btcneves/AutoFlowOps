import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReportGenerateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    period_start: datetime
    period_end: datetime

    @field_validator("period_start", "period_end")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @model_validator(mode="after")
    def validate_period(self) -> "ReportGenerateRequest":
        if self.period_start > self.period_end:
            raise ValueError("period_start must be before or equal to period_end")
        return self


class ReportSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    format: str
    period_start: datetime
    period_end: datetime
    created_at: datetime
    created_by: uuid.UUID | None


class ReportRead(ReportSummaryRead):
    content: str | None
