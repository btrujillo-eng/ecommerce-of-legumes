import os

import psycopg


def test_alembic_created_commerce_tables_and_order_columns() -> None:
    with psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name IN "
                "('cart_items', 'outbox_events', 'orders', 'restore_codes')"
            )
            tables = {row[0] for row in cursor.fetchall()}
            assert {"cart_items", "outbox_events", "orders", "restore_codes"} <= tables

            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'orders'"
            )
            order_columns = {row[0] for row in cursor.fetchall()}
            assert {
                "checkout_key",
                "payment_transaction_id",
                "payment_failed_at",
                "delivery_attempts",
            } <= order_columns
