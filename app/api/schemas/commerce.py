from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus, UnitOfMeasure

PositiveQuantity = Annotated[int, Field(gt=0)]
PositivePrice = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: ProductName
    price: PositivePrice
    stock: Annotated[int, Field(gt=0)]
    section_name: Annotated[str, Field(min_length=2, max_length=30)]
    unit_of_measure: UnitOfMeasure = UnitOfMeasure.KILOGRAM
    image_path: Annotated[str | None, Field(max_length=255)] = None


class ProductPriceUpdateRequest(BaseModel):
    price: PositivePrice


class ProductStockUpdateRequest(BaseModel):
    stock: Annotated[int, Field(gt=0)]


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: Decimal
    unit_of_measure: UnitOfMeasure
    stock: int
    image_path: str | None
    section_id: int


class CartItemCreateRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: PositiveQuantity


class CartItemResponse(BaseModel):
    product_id: int
    name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: Decimal
    currency: str = "COP"


class CheckoutAddress(BaseModel):
    street: Annotated[str, Field(min_length=5, max_length=80)]
    details: Annotated[str, Field(min_length=3, max_length=120)]
    city: Annotated[str, Field(min_length=2, max_length=60)]
    phone_number: Annotated[str, Field(pattern=r"^\d{10}$")]


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderResponse(BaseModel):
    id: int
    total_price: Decimal
    payment_method: PaymentMethods
    payment_status: PaymentStatus
    delivery_status: DeliveryStatus
    shipping_street: str
    shipping_details: str
    shipping_city: str
    phone_number: str
    created_at: datetime
    items: list[OrderItemResponse]


class CheckoutResponse(BaseModel):
    order: OrderResponse
    message: str
    transaction_id: str | None = None


class ReceiptResponse(BaseModel):
    receipt_number: str
    issued_at: datetime
    order: OrderResponse
    payment_transaction_id: str
    currency: str = "COP"
