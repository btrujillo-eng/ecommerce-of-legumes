import logging

import bcrypt

from app.domain.ports import IPasswordHasher

logger = logging.getLogger(__name__)

class PasswordHasher(IPasswordHasher):
    def apply_hash(self, password: str) -> str:
        hashed_bytes = bcrypt.hashpw(password.encode(), bcrypt.gensalt(14))
        
        return hashed_bytes.decode()
    
    def check_password(self, hashed_password: str, password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), hashed_password.encode())
        except TypeError:
            logger.critical("Passwords must be bytes or enconding string type", exc_info=True)
            return False
        except ValueError as e:
            logger.critical("Validation error: %s", e)
            return False