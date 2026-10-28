"""Bootstrap existing ORM schema and add checkout/outbox support.

Revision ID: 20261028_01
Revises:
Create Date: 2026-10-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.infrastructure.persistence.models import Base

revision = "20261028_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # This repository had no checked-in migration history. Create any missing ORM tables first.
    Base.metadata.create_all(bind=bind)
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        if "checkout_key" not in columns:
            op.add_column("orders", sa.Column("checkout_key", sa.String(255), nullable=True))
        if "payment_transaction_id" not in columns:
            op.add_column("orders", sa.Column("payment_transaction_id", sa.String(255), nullable=True))
        if "payment_failed_at" not in columns:
            op.add_column("orders", sa.Column("payment_failed_at", sa.DateTime(timezone=True), nullable=True))
        if "delivery_attempts" not in columns:
            op.add_column("orders", sa.Column("delivery_attempts", sa.Integer(), server_default="0", nullable=False))
        constraints = inspect(bind).get_unique_constraints("orders")
        if not any(constraint.get("column_names") == ["checkout_key"] for constraint in constraints):
            op.create_unique_constraint("uq_orders_checkout_key", "orders", ["checkout_key"])

    if "restore_codes" in tables:
        columns = {column["name"] for column in inspect(bind).get_columns("restore_codes")}
        if "attempts" not in columns:
            op.add_column("restore_codes", sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("orders")}
        constraints = {constraint.get("name") for constraint in inspector.get_unique_constraints("orders")}
        if "uq_orders_checkout_key" in constraints:
            op.drop_constraint("uq_orders_checkout_key", "orders", type_="unique")
        for column in ("delivery_attempts", "payment_failed_at", "payment_transaction_id", "checkout_key"):
            if column in columns:
                op.drop_column("orders", column)
    if "restore_codes" in tables:
        columns = {column["name"] for column in inspector.get_columns("restore_codes")}
        if "attempts" in columns:
            op.drop_column("restore_codes", "attempts")
    op.drop_table("outbox_events")
    op.drop_table("cart_items")
