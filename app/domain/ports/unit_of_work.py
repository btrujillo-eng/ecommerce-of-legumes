from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from app.domain.ports.restore_code_repository import IRestoreCodeRepository
from app.domain.ports.user_repository import IUserRepository


class IUnitOfWork(ABC):
    # The property decorator allows the function to be treated as an entity. 
    @property
    @abstractmethod
    def user(self) -> IUserRepository | None: ...
    
    @property
    @abstractmethod
    def restore_code(self) -> IRestoreCodeRepository | None: ...
    
    @abstractmethod
    async def commit(self) -> None: ...
    
    @abstractmethod
    async def rollback(self) -> None: ...
    
    @abstractmethod
    async def __aenter__(self) -> Self: ...
    
    @abstractmethod
    async def __aexit__(self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None
    ) -> bool | None: ...