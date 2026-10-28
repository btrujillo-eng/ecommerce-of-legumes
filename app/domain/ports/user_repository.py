from abc import ABC, abstractmethod

from app.infrastructure.dtos import (
    RegisteredUserData,
    RegisterUserData,
    UpdatedUserInfo,
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
    async def get_user_by_email_for_update(self, email: str) -> UserForAuthentication | None: ...
    
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> UserForAuthentication | None: ...
    
    @abstractmethod
    async def add_user(self, user_data: RegisterUserData, password_hash: str) -> RegisteredUserData: ...
    
    @abstractmethod
    async def update_password(self, user_id: int, hashed_password: str) -> UpdatedUserInfo: ...