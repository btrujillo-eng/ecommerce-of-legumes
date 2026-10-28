import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.domain.enums import UserRole

Email = Annotated[EmailStr, Field(min_length=5, max_length=255, description="User's email")]
PhoneNumber = Annotated[str, Field(min_length=10, max_length=10, pattern=r"^\d+$", description="User's phone number")]
Name = Annotated[str, Field(min_length=3, max_length=15, pattern=r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ]+$")]
Surname = Annotated[str, Field(min_length=3, max_length=17, pattern=r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ]+$")]


class ContactInfoRequest(BaseModel):
    email: Email
    phone_number: PhoneNumber | None = None


class UserDataRequest(BaseModel):
    first_name: Name
    middle_name: Name | None = None
    first_surname: Surname
    middle_surname: Surname | None = None
    contact_info: ContactInfoRequest


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name
    middle_name: Name | None = None
    first_surname: Surname
    middle_surname: Surname | None = None
    contact_info: ContactInfoRequest
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password):
            raise ValueError("La contraseña debe incluir mayúsculas y minúsculas.")
        if not re.search(r"\d", password) or not re.search(r"[^A-Za-z0-9]", password):
            raise ValueError("La contraseña debe incluir un número y un carácter especial.")
        return value


class UserResponse(BaseModel):
    user_id: int = Field(description="User's id")
    first_name: Name
    first_surname: Surname
    user_role: UserRole
    is_active: bool
