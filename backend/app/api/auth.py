from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserRead
from app.services.audit import client_ip, log_action
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await session.execute(
        select(User).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        await log_action(
            session,
            action="auth.login_failure",
            status="failure",
            ip_address=client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            metadata={"email": payload.email},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        await log_action(
            session,
            action="auth.login_failure",
            status="failure",
            user_id=user.id,
            ip_address=client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            metadata={"reason": "account_inactive"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user.last_login_at = datetime.now(UTC)
    await log_action(
        session,
        action="auth.login_success",
        user_id=user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()

    token = create_access_token(str(user.id), user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
