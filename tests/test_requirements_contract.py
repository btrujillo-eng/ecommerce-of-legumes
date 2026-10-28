from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.schemas.commerce import (
    CartItemCreateRequest,
    CheckoutAddress,
    ProductCreateRequest,
    ProductPriceUpdateRequest,
    ProductStockUpdateRequest,
)
from app.api.schemas.user import ContactInfoRequest, UserCreateRequest
from app.domain.enums import UnitOfMeasure


def test_registration_requires_strong_password_and_does_not_accept_role_escalation() -> None:
    base = {
        "first_name": "Brayan",
        "first_surname": "Trujillo",
        "contact_info": {"email": "brayan@example.com"},
        "password": "StrongPass1!",
    }
    assert UserCreateRequest.model_validate(base).password.get_secret_value() == "StrongPass1!"

    with pytest.raises(ValidationError):
        UserCreateRequest.model_validate({**base, "user_role": "store_manager"})
    with pytest.raises(ValidationError):
        UserCreateRequest.model_validate({**base, "password": "weakpassword"})


def test_cart_quantity_must_be_positive_integer() -> None:
    assert CartItemCreateRequest(product_id=1, quantity=2).quantity == 2
    with pytest.raises(ValidationError):
        CartItemCreateRequest(product_id=1, quantity=0)


def test_product_price_and_stock_validation() -> None:
    product = ProductCreateRequest(
        name="Tomate",
        price=Decimal("3500.00"),
        stock=10,
        section_name="Verduras",
        unit_of_measure=UnitOfMeasure.KILOGRAM,
    )
    assert product.price == Decimal("3500.00")
    with pytest.raises(ValidationError):
        ProductPriceUpdateRequest(price=Decimal("0"))
    with pytest.raises(ValidationError):
        ProductStockUpdateRequest(stock=-1)


def test_checkout_requires_valid_address_and_colombian_phone() -> None:
    address = CheckoutAddress(
        street="Calle 10",
        details="Casa 20, portería",
        city="Medellín",
        phone_number="3001234567",
    )
    assert address.phone_number == "3001234567"
    with pytest.raises(ValidationError):
        CheckoutAddress(
            street="Calle 10",
            details="Casa 20",
            city="Medellín",
            phone_number="123",
        )


def test_email_contact_is_validated() -> None:
    assert ContactInfoRequest(email="buyer@example.com").email == "buyer@example.com"
    with pytest.raises(ValidationError):
        ContactInfoRequest(email="not-an-email")
