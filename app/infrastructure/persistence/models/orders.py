from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Identity, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.enum_utils import get_enum_value

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.order_items import OrderItem
    from app.infrastructure.persistence.models.users import User
    
class Order(Base):
    __tablename__ = 'orders'
    
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    courier_id: Mapped[int | None] = mapped_column(Integer)
    total_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    delivery_status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus, name='delivery_status', values_callable=get_enum_value))
    payment_method: Mapped[PaymentMethods] = mapped_column(Enum(PaymentMethods, name='payment_method', values_callable=get_enum_value))
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name='payment_status', values_callable=get_enum_value))
    shipping_street: Mapped[str] = mapped_column(String(80))
    shipping_details: Mapped[str] = mapped_column(String(120))
    shipping_city: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.now())
    phone_number: Mapped[str] = mapped_column(String(10))
    
    user: Mapped[User] = relationship(back_populates='orders')
    order_items: Mapped[list[OrderItem]] = relationship(back_populates='order')