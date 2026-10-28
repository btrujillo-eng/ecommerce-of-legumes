import asyncio
import html
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import resend
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus
from app.infrastructure.config import Settings
from app.infrastructure.persistence.models import Order, OrderItem, OutboxEvent, Product

logger = logging.getLogger(__name__)


class PaymentOutboxWorker:
    """Durable email delivery and delayed stock release for failed card payments."""

    MAX_ATTEMPTS = 8
    POLL_SECONDS = 2
    LEASE_SECONDS = 120

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings

    async def run(self) -> None:
        while True:
            try:
                await self.release_expired_reservations()
                event_id = await self._claim_one()
                if event_id is None:
                    await asyncio.sleep(self.POLL_SECONDS)
                else:
                    await self._deliver(event_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Payment outbox worker iteration failed")
                await asyncio.sleep(self.POLL_SECONDS)

    async def _claim_one(self) -> int | None:
        now = datetime.now(UTC)
        async with self.session_factory() as session:
            async with session.begin():
                expired_final_attempts = (await session.scalars(
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.status == "processing",
                        OutboxEvent.locked_until < now,
                        OutboxEvent.attempts >= self.MAX_ATTEMPTS,
                    )
                    .with_for_update(skip_locked=True)
                )).all()
                for expired_event in expired_final_attempts:
                    expired_event.status = "failed"
                    expired_event.locked_until = None
                    expired_event.last_error = expired_event.last_error or "Worker lease expired during final attempt."

                statement = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.attempts < self.MAX_ATTEMPTS,
                        or_(
                            (OutboxEvent.status == "pending") & (OutboxEvent.available_at <= now),
                            (OutboxEvent.status == "processing") & (OutboxEvent.locked_until < now),
                        ),
                    )
                    .order_by(OutboxEvent.created_at)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                event = (await session.execute(statement)).scalar_one_or_none()
                if event is None:
                    return None
                event.status = "processing"
                event.attempts += 1
                event.locked_until = now + timedelta(seconds=self.LEASE_SECONDS)
                return event.id

    async def _deliver(self, event_id: int) -> None:
        async with self.session_factory() as session:
            event = await session.get(OutboxEvent, event_id)
            if event is None:
                return
            payload = dict(event.payload)
            event_type = event.event_type

        try:
            await asyncio.to_thread(self._send_email, event_type, payload)
        except Exception as exc:
            logger.exception("Email delivery failed for outbox event %s", event_id)
            await self._retry(event_id, str(exc))
            return

        async with self.session_factory() as session:
            event = await session.get(OutboxEvent, event_id)
            if event is not None:
                event.status = "sent"
                event.processed_at = datetime.now(UTC)
                event.locked_until = None
                event.last_error = None
                await session.commit()

    def _send_email(self, event_type: str, payload: dict[str, Any]) -> None:
        resend.api_key = self.settings.resend_api_key.get_secret_value()
        name = html.escape(str(payload.get("first_name", "cliente")))
        email = str(payload["email"])
        if event_type == "payment.card.succeeded":
            transaction = html.escape(str(payload["transaction_id"]))
            amount = html.escape(str(payload["amount"]))
            currency = html.escape(str(payload["currency"]).upper())
            created = html.escape(str(payload["created_at"]))
            network = html.escape(str(payload["processing_network"]))
            digits = html.escape(str(payload["last_digits"]))
            subject = f"Confirmación de pago {transaction}"
            body = f"<h2>Pago confirmado</h2><p>Hola {name}, tu pago fue aprobado.</p><p>Transacción: {transaction}</p><p>Total: {amount} {currency}</p><p>Fecha: {created}</p><p>Tarjeta: {network} terminada en {digits}</p>"
        elif event_type == "payment.card.failed":
            transaction = html.escape(str(payload["transaction_id"]))
            message = html.escape(str(payload.get("message", "El pago fue rechazado.")))
            subject = f"Pago rechazado {transaction}"
            body = f"<h2>No pudimos procesar tu pago</h2><p>Hola {name}, el pago {transaction} fue rechazado.</p><p>{message}</p><p>No vuelvas a ingresar los datos de tu tarjeta si no estás seguro del resultado; consulta el estado del pedido.</p>"
        elif event_type == "payment.cash.instructions":
            order_id = html.escape(str(payload["order_id"]))
            amount = html.escape(str(payload["amount"]))
            currency = html.escape(str(payload["currency"]).upper())
            address = html.escape(f"{payload['street']}, {payload['details']}, {payload['city']}")
            subject = f"Instrucciones de pago en efectivo para el pedido {order_id}"
            body = f"<h2>Pedido registrado</h2><p>Hola {name}, tu pedido {order_id} quedó pendiente de pago en efectivo.</p><p>Total: {amount} {currency}</p><p>Dirección de entrega: {address}</p><p>Entrega el valor total al domiciliario al recibir tu pedido.</p>"
        else:
            raise ValueError(f"Unsupported outbox event type: {event_type}")

        resend.Emails.send({
            "from": self.settings.resend_from_email,
            "to": [email],
            "subject": subject,
            "html": f"<html><body>{body}</body></html>",
        })

    async def _retry(self, event_id: int, error: str) -> None:
        async with self.session_factory() as session:
            event = await session.get(OutboxEvent, event_id)
            if event is None:
                return
            event.locked_until = None
            event.last_error = error[:1000]
            if event.attempts >= self.MAX_ATTEMPTS:
                event.status = "failed"
            else:
                event.status = "pending"
                event.available_at = datetime.now(UTC) + timedelta(
                    seconds=min(30 * (2 ** (event.attempts - 1)), 3600)
                )
            await session.commit()

    async def release_expired_reservations(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(minutes=10)
        async with self.session_factory() as session:
            async with session.begin():
                orders = (await session.scalars(
                    select(Order)
                    .where(
                        Order.payment_method == PaymentMethods.CARD,
                        Order.payment_status == PaymentStatus.FAILED,
                        Order.delivery_status == DeliveryStatus.PENDING,
                        Order.payment_failed_at <= cutoff,
                    )
                    .with_for_update(skip_locked=True)
                    .limit(50)
                )).all()
                for order in orders:
                    items = (await session.scalars(
                        select(OrderItem).where(OrderItem.order_id == order.id)
                    )).all()
                    for item in items:
                        product = await session.scalar(
                            select(Product).where(Product.id == item.product_id).with_for_update()
                        )
                        if product is not None:
                            product.stock += item.quantity
                    order.delivery_status = DeliveryStatus.CANCELED
                    logger.info("Released stock for canceled failed payment order %s", order.id)
