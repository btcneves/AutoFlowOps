import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.user import PasswordReset, UserCreate, UserRead, UserUpdate
from app.services.audit import client_ip, log_action
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["users"])

_ALLOWED_ROLES = {"admin", "operator", "viewer"}


async def _get_or_404(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _active_admin_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(User).where(User.role == "admin", User.is_active.is_(True))
    )
    return len(result.scalars().all())


@router.get("", response_model=list[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[UserRead]:
    result = await session.execute(select(User).order_by(User.created_at.asc()))
    return [UserRead.model_validate(u) for u in result.scalars().all()]


@router.post("", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    if payload.role not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of: {', '.join(sorted(_ALLOWED_ROLES))}",
        )
    existing = await session.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already in use")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    await session.flush()
    await log_action(
        session,
        action="users.create",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"email": payload.email, "role": payload.role},
    )
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    user = await _get_or_404(session, user_id)

    updates = payload.model_dump(exclude_unset=True)

    if "role" in updates and updates["role"] not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"role must be one of: {', '.join(sorted(_ALLOWED_ROLES))}",
        )

    if updates.get("is_active") is False and user.role == "admin":
        if await _active_admin_count(session) <= 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot deactivate the last active admin account. "
                    "Promote another user to admin first."
                ),
            )

    for field, value in updates.items():
        setattr(user, field, value)

    await log_action(
        session,
        action="users.update",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"updated_fields": list(updates.keys())},
    )
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.post("/{user_id}/reset-password", status_code=200)
async def reset_password(
    user_id: uuid.UUID,
    payload: PasswordReset,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, str]:
    user = await _get_or_404(session, user_id)
    user.password_hash = hash_password(payload.new_password)
    await log_action(
        session,
        action="users.reset_password",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    return {"detail": "Password updated successfully"}


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    user = await _get_or_404(session, user_id)

    if user.id == admin.id:
        raise HTTPException(
            status_code=409, detail="Cannot delete your own account"
        )

    if user.role == "admin" and await _active_admin_count(session) <= 1:
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete the last active admin account. "
                "Promote another user to admin first."
            ),
        )

    await log_action(
        session,
        action="users.delete",
        resource_type="user",
        resource_id=str(user.id),
        user_id=admin.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"email": user.email, "role": user.role},
    )
    await session.delete(user)
    await session.commit()
