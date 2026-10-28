from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.user_registration import get_register_user
from app.api.schemas import UserCreateRequest, UserResponse
from app.application import RegisterUserUseCase
from app.domain.enums import UserRole
from app.exceptions import (
    EmailAlreadyExistsError,
    RepositoryNotInitializedError,
    UnitWorkIsInactiveError,
)
from app.infrastructure.dtos import RegisterUserData

router = APIRouter(prefix="/register", tags=["registration"])


@router.post("/user/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreateRequest,
    repository: RegisterUserUseCase = Depends(get_register_user),
) -> UserResponse:
    try:
        to_register = RegisterUserData(
            first_name=user_data.first_name,
            middle_name=user_data.middle_name,
            first_surname=user_data.first_surname,
            middle_surname=user_data.middle_surname,
            email=str(user_data.contact_info.email).lower(),
            password=user_data.password.get_secret_value(),
            user_role=UserRole.CUSTOMER.value,
        )
        user = await repository.register(to_register)
        return UserResponse(
            user_id=user.user_id,
            first_name=user.first_name,
            first_surname=user.first_surname,
            user_role=UserRole(user.user_role),
            is_active=user.is_active,
        )
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="El email ingresado ya existe en el sistema.") from None
    except (RepositoryNotInitializedError, UnitWorkIsInactiveError):
        raise HTTPException(
            status_code=503,
            detail="El servicio de registro de usuario está temporalmente fuera de servicio.",
        ) from None
