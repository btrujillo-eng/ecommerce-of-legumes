from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus


@dataclass(slots=True)
class Order:
    """Domain entity for order/payment/delivery state transitions."""

    order_id: int | None
    user_id: int
    total_price: Decimal
    payment_method: PaymentMethods
    payment_status: PaymentStatus = PaymentStatus.PENDING
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    delivery_attempts: int = 0

    def mark_payment_succeeded(self) -> None:
        if self.payment_status == PaymentStatus.FAILED:
            raise ValueError("A failed payment cannot be marked as successful without reconciliation.")
        self.payment_status = PaymentStatus.SUCCEDED

    def mark_payment_failed(self) -> None:
        if self.payment_method != PaymentMethods.CARD:
            raise ValueError("Only card payments can be marked as declined.")
        if self.payment_status == PaymentStatus.SUCCEDED:
            raise ValueError("A successful payment cannot be marked as failed.")
        self.payment_status = PaymentStatus.FAILED

    def mark_packaged(self) -> None:
        can_pack = (
            self.payment_status == PaymentStatus.SUCCEDED
            or (
                self.payment_method == PaymentMethods.CASH
                and self.payment_status == PaymentStatus.PENDING
            )
        )
        if self.delivery_status != DeliveryStatus.PENDING or not can_pack:
            raise ValueError("The order is not eligible for packaging.")
        self.delivery_status = DeliveryStatus.PACKAGED

    def pick_up(self) -> None:
        if self.delivery_status not in {
            DeliveryStatus.PACKAGED,
            DeliveryStatus.RETURNED_TO_WAREHOUSE,
        }:
            raise ValueError("The order is not available for pickup.")
        if self.delivery_attempts >= 2:
            raise ValueError("The order has exhausted its delivery attempts.")
        self.delivery_attempts += 1
        self.delivery_status = DeliveryStatus.IN_TRANSIT

    def confirm_cash_payment(self) -> None:
        if (
            self.payment_method != PaymentMethods.CASH
            or self.payment_status != PaymentStatus.PENDING
            or self.delivery_status != DeliveryStatus.IN_TRANSIT
        ):
            raise ValueError("Cash can only be confirmed for an assigned order in transit.")
        self.payment_status = PaymentStatus.SUCCEDED

    def complete_delivery(self) -> None:
        if self.delivery_status != DeliveryStatus.IN_TRANSIT:
            raise ValueError("Only an order in transit can be delivered.")
        if (
            self.payment_method == PaymentMethods.CASH
            and self.payment_status != PaymentStatus.SUCCEDED
        ):
            raise ValueError("Cash payment must be confirmed before delivery is completed.")
        self.delivery_status = DeliveryStatus.DELIVERED

    def report_customer_unavailable(self) -> None:
        if self.delivery_status != DeliveryStatus.IN_TRANSIT:
            raise ValueError("Only an order in transit can have a failed delivery attempt.")
        self.delivery_status = (
            DeliveryStatus.RETURNED_TO_WAREHOUSE
            if self.delivery_attempts < 2
            else DeliveryStatus.CANCELED
        )
