import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


async def _get_workspace_or_404(
    session: AsyncSession, workspace_id: uuid.UUID
) -> Workspace:
    result = await session.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[WorkspaceRead]:
    result = await session.execute(select(Workspace).order_by(Workspace.created_at))
    return [WorkspaceRead.model_validate(w) for w in result.scalars().all()]


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> WorkspaceRead:
    existing = await session.execute(
        select(Workspace).where(Workspace.slug == payload.slug)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Slug already in use")
    workspace = Workspace(name=payload.name, slug=payload.slug)
    session.add(workspace)
    await session.commit()
    await session.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> WorkspaceRead:
    workspace = await _get_workspace_or_404(session, workspace_id)
    if payload.name is not None:
        workspace.name = payload.name
    await session.commit()
    await session.refresh(workspace)
    return WorkspaceRead.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> None:
    workspace = await _get_workspace_or_404(session, workspace_id)
    if workspace.is_default:
        raise HTTPException(
            status_code=400, detail="Cannot delete the default workspace"
        )
    await session.delete(workspace)
    await session.commit()


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[WorkspaceMemberRead]:
    await _get_workspace_or_404(session, workspace_id)
    result = await session.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id
        )
    )
    return [WorkspaceMemberRead.model_validate(m) for m in result.scalars().all()]


@router.post(
    "/{workspace_id}/members", response_model=WorkspaceMemberRead, status_code=201
)
async def add_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceMemberCreate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> WorkspaceMemberRead:
    await _get_workspace_or_404(session, workspace_id)
    existing = await session.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="User is already a member")
    membership = WorkspaceMembership(
        workspace_id=workspace_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    session.add(membership)
    await session.commit()
    await session.refresh(membership)
    return WorkspaceMemberRead.model_validate(membership)


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> None:
    result = await session.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found")
    await session.delete(membership)
    await session.commit()
