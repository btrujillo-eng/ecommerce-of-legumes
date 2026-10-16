from abc import ABC, abstractmethod

from app.infrastructure.dtos import (
    RegisteredUserData,
    RegisterUserData,
    UserForAuthentication,
)


class IUserRepository(ABC):
    """
    Interface for user repository.
    
    Any class that impelement this interface must define 'get_user_by_email', 'add_user' methods.
    """
    @abstractmethod
    async def get_user_by_email(self, email: str) -> UserForAuthentication | None: ...
    
    @abstractmethod
    async def add_user(self, user_data: RegisterUserData, password_hash: str) -> RegisteredUserData: ...