from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(description="Access token generated for the system")
    token_type: str = "bearer"
    
class TokenData(BaseModel):
    user_id: int | None = None
    