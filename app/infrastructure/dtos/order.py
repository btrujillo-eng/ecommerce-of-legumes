from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderData:
    user_id: int
    total_price: Decimal
    payment_method: str
    payment_status: str
    shipping_street: str
    shipping_details: str
    shipping_city: str
    phone_number: str
    
@dataclass(frozen=True, slots=True)    
class RegisteredOrder:
    order_id: int
    delivery_status: str
    created_at: str
    total_price: Decimal
    order_details: list[str]