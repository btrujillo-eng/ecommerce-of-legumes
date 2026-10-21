from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Identity, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.domain.enums import UnitOfMeasure
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.enum_utils import get_enum_value

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.order_items import OrderItem
    from app.infrastructure.persistence.models.product_section import ProductSection

class Product(Base):
    __tablename__ = 'products'
    
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(Enum(UnitOfMeasure, name='unit_of_measure', values_callable=get_enum_value))
    stock: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.now())
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section_id: Mapped[int] = mapped_column(Integer, ForeignKey('product_sections.id'))
    
    section: Mapped[ProductSection] = relationship(back_populates='products')
    order_items: Mapped[list[OrderItem]] = relationship(back_populates='product')