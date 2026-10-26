from abc import ABC, abstractmethod


class IHasher(ABC):
    """
    Interface for password hasher.
    
    Any class that implemet this interface must define the 'apply_hash' and 'check_password' methods.
    
    Methods:
        apply_hash(plain_text: str) -> str:
            Is responsible for applying the hash to the text.
            
        check_password(hashed_text: str, plain_text: str) -> bool:
            Is responsible of verifying that the text entered by the user's matches with the text
            registered in the database.
    """
    @abstractmethod
    def apply_hash(self, plain_text: str) -> str: ...
    
    @abstractmethod
    def check_hash(self, hashed_text: str, plain_text: str) -> bool: ...