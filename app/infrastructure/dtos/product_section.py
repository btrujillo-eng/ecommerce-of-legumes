from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterProductSectionData:
    section_name: str
    
    
@dataclass(frozen=True, slots=True)
class RegisteredProductSection:
    id: int
    section_name: str