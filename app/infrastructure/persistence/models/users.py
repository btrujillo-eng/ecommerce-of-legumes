from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Identity, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.domain.enums import UserRole
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.enum_utils import get_enum_value

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.orders import Order
    from app.infrastructure.persistence.models.restore_codes import RestoreCode

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(20))
    middle_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_surname: Mapped[str] = mapped_column(String(20))
    middle_surname: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    user_role: Mapped[UserRole] = mapped_column(Enum(UserRole, name='user_role',  values_callable=get_enum_value))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())
    
    orders: Mapped[list[Order]] = relationship(back_populates='user')
    restore_codes: Mapped[list[RestoreCode]] = relationship(back_populates='user')
    