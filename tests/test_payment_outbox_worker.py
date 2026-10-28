from types import SimpleNamespace

from pydantic import SecretStr

from app.infrastructure.notifications.payment_outbox_worker import PaymentOutboxWorker


def test_card_confirmation_email_escapes_untrusted_html(monkeypatch) -> None:
    sent = {}
    monkeypatch.setattr(
        "app.infrastructure.notifications.payment_outbox_worker.resend.Emails.send",
        lambda payload: sent.update(payload),
    )
    settings = SimpleNamespace(
        resend_api_key=SecretStr("test-key"),
        resend_from_email="sender@example.com",
    )
    worker = PaymentOutboxWorker(session_factory=None, settings=settings)
    worker._send_email(
        "payment.card.succeeded",
        {
            "email": "buyer@example.com",
            "first_name": "<script>alert(1)</script>",
            "transaction_id": "ch_test_123",
            "amount": "25000.00",
            "currency": "cop",
            "created_at": "2026-10-28T10:00:00+00:00",
            "processing_network": "Visa",
            "last_digits": "4242",
        },
    )
    assert sent["to"] == ["buyer@example.com"]
    assert "&lt;script&gt;" in sent["html"]
    assert "<script>" not in sent["html"]
    assert "4242" in sent["html"]


def test_cash_instructions_email_does_not_require_card_data(monkeypatch) -> None:
    sent = {}
    monkeypatch.setattr(
        "app.infrastructure.notifications.payment_outbox_worker.resend.Emails.send",
        lambda payload: sent.update(payload),
    )
    settings = SimpleNamespace(
        resend_api_key=SecretStr("test-key"),
        resend_from_email="sender@example.com",
    )
    worker = PaymentOutboxWorker(session_factory=None, settings=settings)
    worker._send_email(
        "payment.cash.instructions",
        {
            "email": "buyer@example.com",
            "first_name": "Brayan",
            "order_id": 15,
            "amount": "25000.00",
            "currency": "cop",
            "street": "Calle 10",
            "details": "Casa 20",
            "city": "Medellín",
        },
    )
    assert "pedido 15" in sent["subject"]
    assert "efectivo" in sent["html"]
