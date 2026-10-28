from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.domain.enums import UserRole

Email = Annotated[EmailStr , Field(min_length=5, max_length=255, description="User's email")]

PhoneNumber = Annotated[str, Field(min_length=10, max_length=10, pattern=r'^\d+$', description="User's phone number")]

Name = Annotated[str, Field(min_length=3, max_length=15, pattern=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ]+$')]

Surname = Annotated[str, Field(min_length=3, max_length=17, pattern=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ]+$')]

class ContactInfoRequest(BaseModel):
    email : Email
    phone_number : PhoneNumber | None = None
    
class UserDataRequest(BaseModel):
    first_name : Name = Field(description="User's first name")
    middle_name : Name | None = Field(description="User's middle name", default=None)
    first_surname : Surname = Field(description="User's first surname")
    middle_surname : Surname | None = Field(description="User's middle surname", default=None)
    contact_info : ContactInfoRequest = Field(description="User's contact info")
    
class UserCreateRequest(BaseModel):
    first_name : Name = Field(description="User's first name")
    middle_name : Name | None = Field(description="User's middle name", default=None)
    first_surname : Surname = Field(description="User's first surname")
    middle_surname : Surname | None = Field(description="User's middle surname", default=None)
    contact_info : ContactInfoRequest = Field(description="User's contact info")
    password: SecretStr
    user_role: UserRole
    
class UserResponse(BaseModel):
    user_id: int = Field(description="User's id")
    first_name : Name = Field(description="User's first name")
    first_surname : Surname = Field(description="User's first surname")
    user_role: UserRole = Field(description="User's role")
    is_active: bool = Field(description="Indicates wheter the user account is active en the system")