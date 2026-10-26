from app.domain.ports import IHasher, IUserRepository
from app.exceptions import AuthenticateUserError, UserIsNotActiveError
from app.infrastructure.dtos import UserForAuthentication


class AuthenticateUserUseCase:
    def __init__(self, password_hasher: IHasher, user_repository: IUserRepository) -> None:
        self.password_hasher = password_hasher
        self.user_repository = user_repository
        
    async def authenticate(self, email: str, password: str) -> UserForAuthentication:
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise AuthenticateUserError("Denegated access to the system")
        
        is_correct = self.password_hasher.check_hash(user.password_hash, password)
        if not is_correct:
            raise AuthenticateUserError("Denegated access to the system")
        
        if not user.is_active:
            raise UserIsNotActiveError("User is not active in the system")
        
        return user