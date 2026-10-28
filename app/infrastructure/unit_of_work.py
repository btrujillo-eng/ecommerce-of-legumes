from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports import IUnitOfWork
from app.exceptions import UnitWorkIsInactiveError
from app.infrastructure.persistence.repositories.postgresql import (
    RestoreCodeRepository,
    UserRepository,
)


class UnitOfWork(IUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
        self.session: AsyncSession | None = None
        self._users: UserRepository | None = None
        self._restore_code: RestoreCodeRepository | None = None
     
    @property
    def user(self) -> UserRepository | None:
        return self._users
    
    @property
    def restore_code(self) -> RestoreCodeRepository | None:
        return self._restore_code
        
        
    async def __aenter__(self) -> Self:
        self.session = self.session_factory()
        
        self._users = UserRepository(self.session)
        return self
        
    async def __aexit__(
        self, 
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None, 
        exc_tb: TracebackType | None
        ) -> bool | None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            if self.session is not None:
                await self.session.close()
                self.session = None
                self._users = None
            
    async def commit(self) -> None:
        if self.session is None:
            raise UnitWorkIsInactiveError("Unit work is not active")
        await self.session.commit()
        
    async def rollback(self) -> None:
        if self.session is not None:
           await self.session.rollback()