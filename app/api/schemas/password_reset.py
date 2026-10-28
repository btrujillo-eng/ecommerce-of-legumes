from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator
import re


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=4, pattern=r"^\d{4}$")
    new_password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not re.search(r"[a-z]", password):
            raise ValueError("La contraseña debe incluir una letra minúscula.")
        if not re.search(r"[A-Z]", password):
            raise ValueError("La contraseña debe incluir una letra mayúscula.")
        if not re.search(r"\d", password):
            raise ValueError("La contraseña debe incluir un número.")
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValueError("La contraseña debe incluir un carácter especial.")
        return value
