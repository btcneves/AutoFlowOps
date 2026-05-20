import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    trigger_type: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    request_method: str | None
    request_url: str | None
    request_headers_masked: str | None
    request_body_masked: str | None
    response_status_code: int | None
    response_body_preview: str | None
    error_message: str | None
    retry_attempt: int
    created_at: datetime
