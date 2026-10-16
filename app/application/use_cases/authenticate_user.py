from app.domain.ports import IPasswordHasher, IUserRepository
from app.exceptions import AuthenticateUserError
from app.infrastructure.dtos import UserForAuthentication


class AuthenticateUserUseCase:
    def __init__(self, password_hasher: IPasswordHasher, user_repository: IUserRepository) -> None:
        self.password_hasher = password_hasher
        self.user_repository = user_repository
        
    async def authenticate(self, email: str, password: str) -> UserForAuthentication:
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise AuthenticateUserError("Denegated access to the system")
        
        is_correct = self.password_hasher.check_password(user.password_hash, password)
        if not is_correct:
            raise AuthenticateUserError("Denegated access to the system")
        
        return user