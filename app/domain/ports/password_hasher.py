from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """
    Interface for password hasher.
    
    Any class that implemet this interface must define the 'apply_hash' and 'check_password' methods.
    
    Methods:
        apply_hash(password: str) -> str:
            Is responsible for applying the hash to the user's password.
            
        check_password(hashed_password: str, password: str) -> bool:
            Is responsible of verifying that the password entered by the user's matches with the password
            registered in the database.
    """
    @abstractmethod
    def apply_hash(self, password: str) -> str: ...
    
    @abstractmethod
    def check_password(self, hashed_password: str, password: str) -> bool: ...