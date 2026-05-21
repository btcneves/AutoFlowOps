"""Shared FastAPI dependencies."""

import uuid

import jwt
import structlog
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.auth import decode_access_token

_bearer = HTTPBearer()

_ROLE_LEVEL = {"admin": 3, "operator": 2, "viewer": 1, "user": 1}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    structlog.contextvars.bind_contextvars(user_id=str(user.id))
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if _ROLE_LEVEL.get(current_user.role, 0) < 3:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_operator(
    current_user: User = Depends(get_current_user),
) -> User:
    if _ROLE_LEVEL.get(current_user.role, 0) < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin access required",
        )
    return current_user


async def get_active_workspace(
    x_workspace_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workspace | None:
    if not x_workspace_id:
        return None
    try:
        ws_uuid = uuid.UUID(x_workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Workspace-ID must be a valid UUID",
        )
    result = await session.execute(select(Workspace).where(Workspace.id == ws_uuid))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    structlog.contextvars.bind_contextvars(workspace_id=str(ws_uuid))
    # Admins can access any workspace; all other roles require explicit membership.
    if _ROLE_LEVEL.get(current_user.role, 0) < 3:
        membership = await session.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == ws_uuid,
                WorkspaceMembership.user_id == current_user.id,
            )
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this workspace",
            )
    return workspace
