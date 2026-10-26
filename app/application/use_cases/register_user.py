from app.domain.ports import IHasher, IUnitOfWork
from app.exceptions import RepositoryNotInitializedError
from app.infrastructure.dtos import RegisteredUserData, RegisterUserData


class RegisterUserUseCase:
    def __init__(self, uow: IUnitOfWork, password_hasher: IHasher):
        self.uow = uow
        self.password_hasher = password_hasher
        
    async def register(self, user_data: RegisterUserData) -> RegisteredUserData:
        password_hash = self.password_hasher.apply_hash(user_data.password)
        async with self.uow as uow:
            if uow.user is None:
                raise RepositoryNotInitializedError("The user repository is not initialized")
            
            user = await uow.user.add_user(user_data, password_hash)
            await uow.commit()
            return user