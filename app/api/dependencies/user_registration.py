from fastapi import Depends

from app.application import RegisterUserUseCase
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.hasher import Hasher
from app.infrastructure.persistence.repositories.postgresql import UserRepository
from app.infrastructure.unit_of_work import UnitOfWork


def get_unit_of_work() -> UnitOfWork:
    return UnitOfWork(AsyncSessionLocal)

def get_password_hasher() -> Hasher:
    return Hasher()

def get_user_repository() -> UserRepository:
    return UserRepository(AsyncSessionLocal())

def get_register_user(
        uow: UnitOfWork = Depends(get_unit_of_work),
        password_hasher: Hasher = Depends(get_password_hasher)
    ) -> RegisterUserUseCase:
    return RegisterUserUseCase(uow, password_hasher)