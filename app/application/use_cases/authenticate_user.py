from pydantic import EmailStr

from app.api.schemas import UserResponse
from app.domain.ports import IPasswordHasher, IUserRepository
from app.exceptions import AuthenticateUserError


class AuthenticateUserUseCase:
    def __init__(self, password_hasher: IPasswordHasher, user_repository: IUserRepository) -> None:
        self.password_hasher = password_hasher
        self.user_repository = user_repository
        
    async def authenticate(self, email: EmailStr, password: str) -> UserResponse:
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise AuthenticateUserError("Denegated access to the system")
        
        is_correct = self.password_hasher.check_password(user.password_hash, password)
        if not is_correct:
            raise AuthenticateUserError("Denegated access to the system")
        
        return UserResponse(
            user_id=user.id,
            first_name=user.first_name,
            email=user.email,
            user_role=user.user_role
        )