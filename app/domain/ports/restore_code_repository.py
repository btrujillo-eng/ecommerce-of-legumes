from abc import ABC, abstractmethod

from app.infrastructure.dtos import (
    GeneratedRestoreCode,
    RestoreCodeData,
    RestoreCodeForUpdatePassword,
)


class IRestoreCodeRepository(ABC):
    @abstractmethod
    async def get_restore_code_by_id(self, code_id: int) -> RestoreCodeForUpdatePassword | None: ...
    
    @abstractmethod
    async def desactivate_restore_code(self, code_id: int) -> bool: ...
    
    @abstractmethod
    async def mark_restore_code_as_used(self, code_id: int) -> bool: ...
    
    @abstractmethod
    async def add_restore_code(self, restore_data: RestoreCodeData) -> GeneratedRestoreCode: ...