from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.infrastructure.config import get_settings

settings = get_settings()

def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] =  {
        'sub': str(user_id),
        'exp': expire
    }
    
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        settings.jwt_algorithm,
        )