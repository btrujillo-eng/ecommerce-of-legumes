import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import stripe
from stripe import StripeError

from app.api.schemas import CardPaymentDataRequest, CardPaymentResponse, PaymentDataRequest, PaymentResponse
from app.domain.card_utils import get_processing_network
from app.domain.constants import STRIPE_TRIAL_TOKENS
from app.domain.enums import PaymentMethods
from app.domain.payment_utils import to_stripe_amount
from app.domain.ports import IPaymentGateway
from app.exceptions import StripeNetworkNotSupportError, StripePaymentMethodError, StripeTokenConfigurationError

logger = logging.getLogger(__name__)


class StripeGateway(IPaymentGateway):
    """Adapter for Stripe card charges. The call is moved off the event loop."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def process_payment(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        stripe.api_key = self.api_key
        amount = to_stripe_amount(payment_data.transaction_amount)
        if not isinstance(payment_data.payment_method, CardPaymentDataRequest):
            raise StripePaymentMethodError("El método de pago debe ser tarjeta.")

        card_number = payment_data.payment_method.card_number.get_secret_value()
        source = get_processing_network(card_number)
        if not source:
            raise StripeNetworkNotSupportError("La red de la tarjeta ingresada no es compatible.")
        token = STRIPE_TRIAL_TOKENS.get(source)
        if not token:
            raise StripeTokenConfigurationError("La red de la tarjeta no tiene un token de prueba configurado.")

        try:
            charge = await asyncio.to_thread(
                stripe.Charge.create,
                amount=amount,
                currency=payment_data.currency.value,
                source=token,
                description=f"Charge for {payment_data.user_data.first_name} {payment_data.user_data.first_surname}",
                idempotency_key=payment_data.idempotency_key or str(uuid4()),
            )
            status_value = str(charge["status"])
            return PaymentResponse(
                currency=charge["currency"],
                transaction_amount=Decimal(str(charge["amount"])) / Decimal("100"),
                transaction_id=str(charge["id"]),
                payment_status=status_value,
                message="Pago exitoso" if status_value == "succeeded" else "Pago no aprobado",
                created_at=datetime.fromtimestamp(charge["created"], tz=UTC),
                payment_method=CardPaymentResponse(
                    method=PaymentMethods.CARD,
                    processing_network=source,
                    last_digits=card_number[-4:],
                ),
            )
        except StripeError as exc:
            if exc.__class__.__name__ != "CardError":
                # Network/API errors can leave the charge outcome uncertain. Do not mark
                # the order failed or release its stock; retry with the same idempotency key.
                logger.exception("Stripe outcome is uncertain; propagating for reconciliation")
                raise
            logger.warning("Stripe declined card payment: %s", exc)
            return PaymentResponse(
                currency=payment_data.currency,
                transaction_amount=payment_data.transaction_amount,
                transaction_id=str(getattr(exc, "request_id", None) or f"declined-{payment_data.idempotency_key or uuid4()}"),
                payment_status="failed",
                message="El pago fue rechazado por el emisor de la tarjeta.",
                created_at=datetime.now(UTC),
                payment_method=CardPaymentResponse(
                    method=PaymentMethods.CARD,
                    processing_network=source,
                    last_digits=card_number[-4:],
                ),
            )
