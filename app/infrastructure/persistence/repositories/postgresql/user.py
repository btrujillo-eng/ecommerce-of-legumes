import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports import IUserRepository
from app.exceptions import (
    EmailAlreadyExistsError,
    UserDoesNotExistError,
    UserRegistrationServiceError,
)
from app.infrastructure.dtos import (
    RegisteredUserData,
    RegisterUserData,
    UpdatedUserInfo,
    UserForAuthentication,
)
from app.infrastructure.persistence.models import User

logger = logging.getLogger(__name__)

class UserRepository(IUserRepository):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        
    def _to_user_auth(self, user: User) -> UserForAuthentication:
        return UserForAuthentication(
            user_id=user.id,
            first_name=user.first_name,
            first_surname=user.first_surname,
            password_hash=user.password_hash,
            user_role=user.user_role,
            is_active=user.is_active
        )
    
    async def get_user_by_email(self, email: str) -> UserForAuthentication | None:
        stmt = select(User).where(User.email == email)
        user = await self.db_session.scalar(stmt)
        if user is None:
            return None
        
        return self._to_user_auth(user)
    
    async def get_user_by_email_for_update(self, email: str) -> UserForAuthentication | None:
            stmt = select(User).where(User.email == email).with_for_update()
            user = await self.db_session.scalar(stmt)
            if user is None:
                return None
            
            return self._to_user_auth(user)
        
    async def get_user_by_id(self, user_id: int) -> UserForAuthentication | None:
        stmt = select(User).where(User.id == user_id)
        user = await self.db_session.scalar(stmt)
        if user is None:
            return None
        
        return self._to_user_auth(user)
        
    async def add_user(self, user_data: RegisterUserData, password_hash: str) -> RegisteredUserData:
        user = User(
            first_name=user_data.first_name,
            middle_name=user_data.middle_name,
            first_surname=user_data.first_surname,
            middle_surname=user_data.middle_surname,
            email=user_data.email,
            password_hash=password_hash,
            user_role=user_data.user_role
        )
        
        try:
            self.db_session.add(user)
            await self.db_session.flush()
            await self.db_session.refresh(user)
            return RegisteredUserData(
                user_id=user.id,
                first_name=user.first_name,
                middle_name=user.middle_name,
                first_surname=user.first_surname,
                middle_surname=user.middle_surname,
                email=user.email,
                user_role=user.user_role,
                is_active=user.is_active
            )
        except IntegrityError as e:
            sqlstate = getattr(e.orig, "sqlstate", None) or getattr(e.orig, "pgcode", None)
            if sqlstate == "23505":
                raise EmailAlreadyExistsError("The email address entered already exists in the system")
            
            logger.error("Could not be insert the user: %s | Error: %s", user_data.first_name, e)
            raise UserRegistrationServiceError("User registration service unavailable")
        
    async def update_password(self, user_id: int, hashed_password: str) -> UpdatedUserInfo:
        stmt = select(User).where(User.id == user_id)
        result = await self.db_session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise UserDoesNotExistError("User does not exist.")
        
        user.password_hash = hashed_password
        await self.db_session.flush()
        return UpdatedUserInfo(
            first_name=user.first_name,
            first_surname=user.first_surname
        )