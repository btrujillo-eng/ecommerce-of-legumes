from fastapi import Depends

from app.application import AuthenticateUserUseCase
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.hasher import Hasher
from app.infrastructure.persistence.repositories.postgresql import UserRepository


def get_password_hasher() -> Hasher:
    return Hasher()

def get_user_repository() -> UserRepository:
    return UserRepository(AsyncSessionLocal())

def get_authenticate_user(
    password_hasher: Hasher = Depends(get_password_hasher),
    user_repository: UserRepository = Depends(get_user_repository)
    ) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(
        password_hasher, user_repository
    )