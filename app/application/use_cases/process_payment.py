import logging

from app.api.schemas import PaymentDataRequest, PaymentResponse
from app.domain.enums import PaymentMethods, PaymentStatus
from app.domain.ports import IPaymentMethodFactory, IShoppingCart
from app.infrastructure.persistence.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class ProcessPaymentUseCase:
    def __init__(
        self,
        shopping_cart: IShoppingCart,
        payment_method_factory: IPaymentMethodFactory,
        outbox_repository: OutboxRepository,
    ) -> None:
        self.shopping_cart = shopping_cart
        self.payment_method_factory = payment_method_factory
        self.outbox_repository = outbox_repository

    async def process(self, payment_data: PaymentDataRequest) -> PaymentResponse:
        total_amount = self.shopping_cart.calculate_total(
            payment_data.transaction_amount,
            payment_data.discount_type,
        )
        data = payment_data.model_copy(update={"transaction_amount": total_amount})
        processor = self.payment_method_factory.create_payment_processor(data.payment_method.method)
        result = await processor.process(data)

        if data.payment_method.method == PaymentMethods.CARD:
            card = result.payment_method
            successful = result.payment_status == PaymentStatus.SUCCEDED.value
            event_type = "payment.card.succeeded" if successful else "payment.card.failed"
            payload = {
                "email": str(data.user_data.contact_info.email),
                "first_name": data.user_data.first_name,
                "transaction_id": result.transaction_id,
                "amount": str(result.transaction_amount),
                "currency": result.currency.value,
                "created_at": result.created_at.isoformat(),
                "processing_network": card.processing_network,
                "last_digits": card.last_digits,
                "message": result.message or "El pago fue rechazado.",
            }
            try:
                await self.outbox_repository.enqueue(
                    event_key=f"{event_type}:{result.transaction_id}",
                    event_type=event_type,
                    payload=payload,
                )
            except Exception:
                # Never change the financial result because notification infrastructure is down.
                logger.exception("Could not enqueue email for transaction %s", result.transaction_id)
        return result
