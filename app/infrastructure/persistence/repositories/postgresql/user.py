import logging

from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UserCreateRequest, UserResponse
from app.domain.ports import IUserRepository
from app.exceptions import EmailAlreadyExistsError
from app.infrastructure.models import User

logger = logging.getLogger(__name__)

class UserRepository(IUserRepository):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
    
    async def get_user_by_email(self, email: EmailStr) -> User | None:
        stmt = select(User).where(User.email == email)
        user = await self.db_session.scalar(stmt)
        
        return user
    
    async def add_user(self, user_data: UserCreateRequest, password_hash: str) -> UserResponse:
        user = User(
            first_name=user_data.first_name,
            middle_name=user_data.middle_name,
            first_surname=user_data.first_surname,
            middle_surname=user_data.middle_surname,
            email=user_data.contact_info.email,
            password_hash=password_hash,
            user_role=user_data.user_role
        )
        
        try:
            self.db_session.add(user)
            await self.db_session.flush()
            await self.db_session.refresh(user)
            return UserResponse(
                user_id=user.id,
                first_name=user.first_name,
                email=user.email,
                user_role=user.user_role
            )
        except IntegrityError as e:
            sqlstate = getattr(e.orig, "sqlstate", None) or getattr(e.orig, "pgcode", None)
            if sqlstate == "23505":
                raise EmailAlreadyExistsError("The email address entered already exists in the system")
            
            logger.error("Could not be insert the user: %s | Error: %s", user_data.first_name, e)
            raise