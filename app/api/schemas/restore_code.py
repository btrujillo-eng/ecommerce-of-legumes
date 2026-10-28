from pydantic import BaseModel, EmailStr, Field


class CreateRestoreCodeRequest(BaseModel):
    email: EmailStr


class CreateRestoreCodeResponse(BaseModel):
    message: str = Field(min_length=1)
    code_id: int | None = None
