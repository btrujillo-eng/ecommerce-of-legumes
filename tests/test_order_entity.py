from decimal import Decimal

import pytest

from app.domain.entities.order import Order
from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


def test_card_order_must_be_paid_before_packaging_and_can_be_delivered() -> None:
    order = Order(1, 10, Decimal("25000.00"), PaymentMethods.CARD)
    with pytest.raises(ValueError):
        order.mark_packaged()
    order.mark_payment_succeeded()
    order.mark_packaged()
    order.pick_up()
    order.complete_delivery()
    assert order.payment_status == PaymentStatus.SUCCEDED
    assert order.delivery_status == DeliveryStatus.DELIVERED


def test_cash_order_requires_payment_confirmation_before_delivery() -> None:
    order = Order(2, 10, Decimal("25000.00"), PaymentMethods.CASH)
    order.mark_packaged()
    order.pick_up()
    with pytest.raises(ValueError):
        order.complete_delivery()
    order.confirm_cash_payment()
    order.complete_delivery()
    assert order.delivery_status == DeliveryStatus.DELIVERED


def test_delivery_has_at_most_two_attempts() -> None:
    order = Order(3, 10, Decimal("25000.00"), PaymentMethods.CARD)
    order.mark_payment_succeeded()
    order.mark_packaged()
    order.pick_up()
    order.report_customer_unavailable()
    assert order.delivery_status == DeliveryStatus.RETURNED_TO_WAREHOUSE
    order.pick_up()
    order.report_customer_unavailable()
    assert order.delivery_status == DeliveryStatus.CANCELED
    with pytest.raises(ValueError):
        order.pick_up()
