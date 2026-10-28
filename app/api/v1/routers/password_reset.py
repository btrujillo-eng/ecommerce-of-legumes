import asyncio
import logging
import secrets
from datetime import UTC, datetime, timedelta

import resend
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.current_user import get_session
from app.api.schemas.password_reset import PasswordResetConfirmRequest, PasswordResetRequest
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.hasher import Hasher
from app.infrastructure.persistence.models import RestoreCode, User

router = APIRouter(prefix="/users/v1/auth/password-reset", tags=["password-reset"])
logger = logging.getLogger(__name__)
GENERIC_MESSAGE = "Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña."


@router.post("/request")
async def request_password_reset(
    body: PasswordResetRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    user = await session.scalar(select(User).where(User.email == str(body.email).lower()).with_for_update())
    if user is None:
        return {"message": GENERIC_MESSAGE}

    await session.execute(
        update(RestoreCode)
        .where(RestoreCode.user_id == user.id, RestoreCode.is_active.is_(True))
        .values(is_active=False)
    )
    code = f"{secrets.randbelow(10000):04d}"
    hasher = Hasher()
    restore = RestoreCode(
        user_id=user.id,
        code_hash=hasher.apply_hash(code),
        attempts=0,
        expired_at=datetime.now(UTC) + timedelta(minutes=10),
        is_active=True,
        was_used=False,
    )
    session.add(restore)
    await session.commit()

    try:
        resend.api_key = settings.resend_api_key.get_secret_value()
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": settings.resend_from_email,
                "to": [user.email],
                "subject": "Código para restablecer tu contraseña",
                "html": f"<p>Tu código de verificación es <strong>{code}</strong>.</p><p>Vence en 10 minutos y permite hasta 5 intentos.</p>",
            },
        )
    except Exception:
        logger.exception("Unable to send password reset email for user id %s", user.id)
    return {"message": GENERIC_MESSAGE}


@router.post("/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user = await session.scalar(select(User).where(User.email == str(body.email).lower()))
    if user is None:
        return {"message": "El código no es válido o ha expirado."}

    now = datetime.now(UTC)
    restore = await session.scalar(
        select(RestoreCode)
        .where(
            RestoreCode.user_id == user.id,
            RestoreCode.is_active.is_(True),
            RestoreCode.was_used.is_(False),
            RestoreCode.expired_at > now,
        )
        .order_by(RestoreCode.id.desc())
        .with_for_update()
    )
    if restore is None:
        return {"message": "El código no es válido o ha expirado."}

    if restore.attempts >= 5:
        restore.is_active = False
        await session.commit()
        return {"message": "Se agotaron los intentos. Solicita un nuevo código."}

    if not Hasher().check_hash(restore.code_hash, body.code):
        restore.attempts += 1
        if restore.attempts >= 5:
            restore.is_active = False
        await session.commit()
        return {"message": "El código no es válido o ha expirado."}

    user.password_hash = Hasher().apply_hash(body.new_password.get_secret_value())
    restore.was_used = True
    restore.is_active = False
    await session.commit()
    return {"message": "Contraseña actualizada correctamente."}
