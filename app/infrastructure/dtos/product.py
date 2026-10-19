from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RegisterProductData:
    product_name: str
    section_id: int
    price: Decimal
    stock: int
    unit_of_measure: str

@dataclass(frozen=True, slots=True)
class RegisteredProduct:
    id: int
    product_name: str
    section_id: int
    price: Decimal
    stock: int
    unit_of_measure: str

@dataclass(frozen=True, slots=True)    
class UpdatedProduct:
    id: int
    name: str
    price: Decimal
    stock: int
    unit_of_measure: str