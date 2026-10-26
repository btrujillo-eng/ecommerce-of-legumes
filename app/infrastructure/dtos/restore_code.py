from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RestoreCodeData:
    user_id: int
    code_hash: str
    expired_at: datetime

@dataclass(frozen=True, slots=True)
class GeneratedRestoreCode:
    code_id: int
    user_id: int
   
@dataclass(frozen=True, slots=True) 
class RestoreCodeForUpdatePassword:
    user_id: int
    code_hash: str
    was_used: bool
    is_active: bool
    expired_at: datetime