import logging

import bcrypt

from app.domain.ports import IHasher

logger = logging.getLogger(__name__)

class Hasher(IHasher):
    def apply_hash(self, plain_text: str) -> str:
        hashed_bytes = bcrypt.hashpw(plain_text.encode(), bcrypt.gensalt(14))
        
        return hashed_bytes.decode()
    
    def check_hash(self, hashed_text: str, plain_text: str) -> bool:
        try:
            return bcrypt.checkpw(plain_text.encode(), hashed_text.encode())
        except TypeError:
            logger.critical("Passwords must be bytes or enconding string type", exc_info=True)
            return False
        except ValueError as e:
            logger.critical("Validation error: %s", e)
            return False