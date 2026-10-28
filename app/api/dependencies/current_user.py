from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError, decode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import UserRole
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.persistence.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/v1/auth/token")


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        user_id = int(subject)
    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_error from None

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(status_code=403, detail="El usuario está inactivo.")
    return user


def require_roles(*allowed_roles: UserRole):
    async def dependency(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta operación.",
            )
        return user
    return dependency
