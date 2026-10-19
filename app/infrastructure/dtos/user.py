from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterUserData:
    first_name: str
    middle_name: str | None
    first_surname: str
    middle_surname: str | None
    email: str
    password: str
    user_role: str
    
@dataclass(frozen=True, slots=True)
class RegisteredUserData:
    user_id: int
    first_name: str
    middle_name: str | None
    first_surname: str
    middle_surname: str | None
    email: str
    user_role: str
    is_active: bool

@dataclass(frozen=True, slots=True)
class UserForAuthentication:
    user_id: int
    first_name: str
    first_surname: str
    password_hash: str
    user_role: str
    is_active: bool

@dataclass(frozen=True, slots=True)   
class AuthenticatedUser:
    user_id: int
    first_name: str
    first_surname: str
    user_role: str
    is_active: bool

@dataclass(frozen=True, slots=True)     
class UpdatedUserInfo:
    first_name: str
    first_surname: str