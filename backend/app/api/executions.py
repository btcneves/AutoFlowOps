import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_active_workspace, get_current_user
from app.models.execution import Execution
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.execution import ExecutionRead

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=list[ExecutionRead])
async def list_executions(
    job_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> list[ExecutionRead]:
    stmt = select(Execution).order_by(Execution.started_at.desc())
    if job_id is not None:
        stmt = stmt.where(Execution.job_id == job_id)
    if status is not None:
        stmt = stmt.where(Execution.status == status)
    if workspace is not None:
        stmt = stmt.where(Execution.workspace_id == workspace.id)
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return [ExecutionRead.model_validate(e) for e in result.scalars().all()]


@router.get("/{execution_id}", response_model=ExecutionRead)
async def get_execution(
    execution_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExecutionRead:
    result = await session.execute(
        select(Execution).where(Execution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionRead.model_validate(execution)
