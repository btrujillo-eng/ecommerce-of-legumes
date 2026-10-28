import logging

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports import IRestoreCodeRepository
from app.exceptions import (
    ThereIsAnActiveRestoreCodeError,
)
from app.infrastructure.dtos import (
    GeneratedRestoreCode,
    RestoreCodeData,
    RestoreCodeForUpdatePassword,
)
from app.infrastructure.persistence.models import RestoreCode

logger = logging.getLogger(__name__)

class RestoreCodeRepository(IRestoreCodeRepository):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        
        
    async def get_restore_code_by_id(self, code_id: int) -> RestoreCodeForUpdatePassword | None:
        stmt = select(RestoreCode).where(RestoreCode.id == code_id)
        restore_code = await self.db_session.scalar(stmt)
        if restore_code is None:
            return None
        
        return RestoreCodeForUpdatePassword(
            user_id=restore_code.user.id,
            code_hash=restore_code.code_hash,
            was_used=restore_code.was_used,
            is_active=restore_code.is_active,
            expired_at=restore_code.expired_at            
        )
    
    async def desactivate_restore_code(self, code_id: int) -> bool:
        stmt = (
            update(RestoreCode)
            .where(
                RestoreCode.user_id == code_id,
                RestoreCode.is_active.is_(True)
            )
            .values(is_active=False)
        )
        
        result = await self.db_session.execute(stmt)
        return result.rowcount > 0 # type: ignore
    
    async def mark_restore_code_as_used(self, code_id: int) -> bool:
        stmt = (
            update(RestoreCode)
            .where(
                RestoreCode.id == code_id,
                RestoreCode.was_used.is_(False),
                RestoreCode.is_active.is_(True)
            )
            .values(was_used=True)
        )
        result = await self.db_session.execute(stmt)
        return result.rowcount > 0 # type: ignore
        
    async def add_restore_code(self, restore_data: RestoreCodeData) -> GeneratedRestoreCode:
        restore_code = RestoreCode(
            user_id=restore_data.user_id,
            code_hash=restore_data.code_hash,
            expired_at=restore_data.expired_at
        )
        try: 
            self.db_session.add(restore_code)
            await self.db_session.flush()
            return GeneratedRestoreCode(
                code_id=restore_code.id,
                user_id=restore_code.user.id
            )
        except IntegrityError as e:
            sqlstate = getattr(e.orig, "sqlstate", None) or getattr(e.orig, "pgcode", None)
            if sqlstate == "23505":
                raise ThereIsAnActiveRestoreCodeError("A restoration code already exists in 'active' state")
            
            raise