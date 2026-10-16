from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.user_registration import get_register_user
from app.api.schemas import UserCreateRequest, UserResponse
from app.application import RegisterUserUseCase
from app.exceptions import (
    EmailAlreadyExistsError,
    RepositoryNotInitializedError,
    UnitWorkIsInactiveError,
)

router = APIRouter(prefix="/register", tags=["regsiter"])
@router.post("/user/", response_model=UserResponse)
async def register_user(
    user_data: UserCreateRequest,
    repository: RegisterUserUseCase = Depends(get_register_user),
    ) -> UserResponse:
    try:
        return await repository.register(user_data)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ingresado ya existe en el sistema."
        )
    except (RepositoryNotInitializedError, UnitWorkIsInactiveError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de registros de usuario está temporalmente fuera de servicio."
        )