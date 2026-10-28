from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RegisteredOrderItem:
    order_item_id: int
    order_id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
