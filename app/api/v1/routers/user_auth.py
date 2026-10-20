from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError, decode

from app.api.dependencies.user_auth import (
    get_authenticate_user,
    get_user_repository,
)
from app.api.schemas import Token, UserResponse
from app.application import AuthenticateUserUseCase
from app.domain.enums import UserRole
from app.exceptions import AuthenticateUserError, UserIsNotActiveError
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.dtos import AuthenticatedUser
from app.infrastructure.jwt_handler import create_access_token
from app.infrastructure.persistence.repositories.postgresql import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/v1/auth/token")

async def get_current_user(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    settings: Annotated[Settings, Depends(get_settings)], 
    token: Annotated[str, Depends(oauth2_scheme)],
    ) -> AuthenticatedUser:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode(
            token, 
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm]
        )
        id = payload.get('sub')
        if not id:
            raise credential_exception
    except InvalidTokenError:
        raise credential_exception
    user = await repository.get_user_by_id(id)
    if user is None:
        raise credential_exception
    
    if user.is_active:
        return AuthenticatedUser(
            user_id=user.user_id,
            first_name=user.first_name,
            first_surname=user.first_surname,
            user_role=user.user_role,
            is_active=user.is_active
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Tu usuario está inactivo. Por favor vuelve a activarlo nuevamente."
    )

router_login = APIRouter(prefix="/users", tags=["token"])
@router_login.post("/v1/auth/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_user: Annotated[AuthenticateUserUseCase, Depends(get_authenticate_user)],
    ) -> Token:
    try:    
        user = await auth_user.authenticate(form_data.username, form_data.password)
        access_token = create_access_token(user.user_id)
        return Token(access_token=access_token)
    except AuthenticateUserError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos"
        )
    except UserIsNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tú usuario está inactivo. Por favor vuelve a activarlo nuevamente."
        )
    
router_home_page  =  APIRouter(prefix="/me", tags=["users"])
@router_home_page.get("/", response_model=UserResponse)
async def read_user_me(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        first_name=user.first_name,
        first_surname=user.first_surname,
        user_role=UserRole(user.user_role),
        is_active=user.is_active
    )