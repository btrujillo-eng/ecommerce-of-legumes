import asyncio
import logging
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from typing import Annotated

import resend
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.current_user import get_current_user, get_session, require_roles
from app.api.dependencies.payment import get_payment_method_factory
from app.api.schemas.commerce import (
    CartItemCreateRequest, CartItemResponse, CartResponse, CheckoutAddress,
    CheckoutResponse, OrderItemResponse, OrderResponse, ProductCreateRequest,
    ProductPriceUpdateRequest, ProductResponse, ProductStockUpdateRequest,
    ReceiptResponse,
)
from app.api.schemas.payment import (
    CashPaymentDataRequest, CardPaymentDataRequest, PaymentDataRequest,
)
from app.api.schemas.user import ContactInfoRequest, UserDataRequest
from app.domain.enums import (
    DeliveryStatus, DiscountStrategy, PaymentMethods, PaymentStatus,
    TypeCurrency, UnitOfMeasure, UserRole,
)
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.persistence.models import (
    CartItem, Order, OrderItem, OutboxEvent, Product, ProductSection, User,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["commerce"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentCustomer = Annotated[User, Depends(require_roles(UserRole.CUSTOMER))]
StoreManager = Annotated[User, Depends(require_roles(UserRole.STORE_MANAGER))]
WarehouseManager = Annotated[User, Depends(require_roles(UserRole.WAREHOUSE_MANAGER))]
PackagingManager = Annotated[User, Depends(require_roles(UserRole.PACKAGING_MANAGER))]
Courier = Annotated[User, Depends(require_roles(UserRole.COURIER))]


def _order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        total_price=order.total_price,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        delivery_status=order.delivery_status,
        shipping_street=order.shipping_street,
        shipping_details=order.shipping_details,
        shipping_city=order.shipping_city,
        phone_number=order.phone_number,
        created_at=order.created_at,
        items=[
            OrderItemResponse(
                product_id=item.product_id,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.unit_price * item.quantity,
            )
            for item in order.order_items
        ],
    )


async def _load_order(session: AsyncSession, order_id: int) -> Order | None:
    return await session.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.order_items).selectinload(OrderItem.product))
    )


def _enqueue_email(
    session: AsyncSession,
    *,
    event_key: str,
    event_type: str,
    payload: dict,
) -> None:
    session.add(OutboxEvent(
        event_key=event_key,
        event_type=event_type,
        payload=payload,
        status="pending",
        attempts=0,
    ))


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> list[ProductResponse]:
    statement = select(Product).options(selectinload(Product.section)).order_by(Product.name)
    if user.user_role == UserRole.CUSTOMER:
        statement = statement.where(Product.stock > 0)
    if q:
        term = q.strip()
        if not term or not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s-]+", term):
            raise HTTPException(status_code=400, detail="La búsqueda solo admite letras y espacios.")
        pattern = f"%{term}%"
        statement = statement.join(ProductSection).where(
            or_(func.lower(Product.name).like(pattern.lower()), func.lower(ProductSection.name).like(pattern.lower()))
        )
    products = (await session.scalars(statement.limit(100))).all()
    return [ProductResponse.model_validate(product) for product in products]


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateRequest,
    session: SessionDep,
    user: StoreManager,
) -> ProductResponse:
    section_name = body.section_name.strip()
    section = await session.scalar(
        select(ProductSection).where(func.lower(ProductSection.name) == section_name.lower())
    )
    if section is None:
        section = ProductSection(name=section_name)
        session.add(section)
        await session.flush()
    duplicate = await session.scalar(
        select(Product.id).where(func.lower(Product.name) == body.name.lower())
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese nombre.")
    product = Product(
        name=body.name,
        price=body.price,
        stock=body.stock,
        unit_of_measure=body.unit_of_measure,
        image_path=body.image_path,
        section_id=section.id,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)


@router.patch("/products/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    product_id: int,
    body: ProductStockUpdateRequest,
    session: SessionDep,
    user: WarehouseManager,
) -> ProductResponse:
    product = await session.get(Product, product_id, with_for_update=True)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    product.stock = body.stock
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)


@router.patch("/products/{product_id}/price", response_model=ProductResponse)
async def update_product_price(
    product_id: int,
    body: ProductPriceUpdateRequest,
    session: SessionDep,
    user: StoreManager,
) -> ProductResponse:
    product = await session.get(Product, product_id, with_for_update=True)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    product.price = body.price
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)


@router.get("/cart", response_model=CartResponse)
async def get_cart(session: SessionDep, user: CurrentCustomer) -> CartResponse:
    rows = (await session.scalars(
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(selectinload(CartItem.product))
        .order_by(CartItem.id)
    )).all()
    items = [
        CartItemResponse(
            product_id=row.product_id,
            name=row.product.name,
            quantity=row.quantity,
            unit_price=row.product.price,
            subtotal=row.product.price * row.quantity,
        )
        for row in rows
    ]
    return CartResponse(items=items, total=sum((item.subtotal for item in items), Decimal("0.00")))


@router.post("/cart/items", response_model=CartResponse, status_code=status.HTTP_200_OK)
async def add_cart_item(
    body: CartItemCreateRequest,
    session: SessionDep,
    user: CurrentCustomer,
) -> CartResponse:
    product = await session.scalar(
        select(Product).where(Product.id == body.product_id).with_for_update()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    existing = await session.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id,
            CartItem.product_id == product.id,
        ).with_for_update()
    )
    new_quantity = body.quantity + (existing.quantity if existing else 0)
    if new_quantity > product.stock:
        raise HTTPException(status_code=409, detail="La cantidad solicitada supera el stock disponible.")
    if existing:
        existing.quantity = new_quantity
    else:
        session.add(CartItem(user_id=user.id, product_id=product.id, quantity=body.quantity))
    await session.commit()
    return await get_cart(session, user)


@router.delete("/cart/items/{product_id}", response_model=CartResponse)
async def remove_cart_item(
    product_id: int,
    session: SessionDep,
    user: CurrentCustomer,
) -> CartResponse:
    item = await session.scalar(select(CartItem).where(
        CartItem.user_id == user.id, CartItem.product_id == product_id
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="El producto no está en tu carrito.")
    await session.delete(item)
    await session.commit()
    return await get_cart(session, user)


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
async def checkout(
    address: CheckoutAddress,
    session: SessionDep,
    user: CurrentCustomer,
    payment_method: CardPaymentDataRequest | CashPaymentDataRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=255)],
    payment_factory=Depends(get_payment_method_factory),
) -> CheckoutResponse:
    key = idempotency_key.strip()
    existing_order = await session.scalar(select(Order).where(Order.checkout_key == key))
    if existing_order is not None:
        loaded = await _load_order(session, existing_order.id)
        return CheckoutResponse(order=_order_response(loaded), message="Esta solicitud de compra ya fue procesada.", transaction_id=loaded.payment_transaction_id)

    cart_rows = (await session.scalars(
        select(CartItem).where(CartItem.user_id == user.id).with_for_update()
    )).all()
    if not cart_rows:
        raise HTTPException(status_code=400, detail="El carrito de compras está vacío.")

    product_ids = sorted({row.product_id for row in cart_rows})
    locked_products = (await session.scalars(
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).all()
    products_by_id = {product.id: product for product in locked_products}
    total = sum((products_by_id[row.product_id].price * row.quantity for row in cart_rows), Decimal("0.00"))
    if total < Decimal("20000.00"):
        raise HTTPException(status_code=400, detail="El valor mínimo del pedido es $20.000 COP.")

    for row in cart_rows:
        product = products_by_id.get(row.product_id)
        if product is None or row.quantity <= 0 or product.stock < row.quantity:
            product_name = product.name if product is not None else f"ID {row.product_id}"
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para el producto {product_name}.")

    order = Order(
        user_id=user.id,
        total_price=total,
        delivery_status=DeliveryStatus.PENDING,
        payment_method=payment_method.method,
        payment_status=PaymentStatus.PENDING,
        shipping_street=address.street,
        shipping_details=address.details,
        shipping_city=address.city,
        phone_number=address.phone_number,
        checkout_key=key,
    )
    session.add(order)
    await session.flush()
    for row in cart_rows:
        product = products_by_id[row.product_id]
        product.stock -= row.quantity
        session.add(OrderItem(
            order_id=order.id,
            product_id=row.product_id,
            unit_price=product.price,
            quantity=row.quantity,
        ))
        await session.delete(row)
    await session.commit()

    user_data = UserDataRequest(
        first_name=user.first_name,
        middle_name=user.middle_name,
        first_surname=user.first_surname,
        middle_surname=user.middle_surname,
        contact_info=ContactInfoRequest(email=user.email, phone_number=address.phone_number),
    )
    payment_data = PaymentDataRequest(
        user_data=user_data,
        currency=TypeCurrency.COP,
        discount_type=DiscountStrategy.NODISCOUNT.value,
        transaction_amount=total,
        payment_method=payment_method,
        idempotency_key=key,
    )
    try:
        processor = payment_factory.create_payment_processor(payment_method.method)
        payment_result = await processor.process(payment_data)
    except Exception:
        logger.exception("Payment processing outcome is uncertain for checkout %s", key)
        raise HTTPException(
            status_code=503,
            detail=f"No fue posible confirmar el resultado del pago. El pedido {order.id} permanece pendiente; consulta GET /orders/{order.id} y reintenta mediante POST /orders/{order.id}/retry-payment con el mismo Idempotency-Key.",
        )

    async with session.begin():
        stored_order = await session.scalar(select(Order).where(Order.id == order.id).with_for_update())
        stored_order.payment_transaction_id = payment_result.transaction_id
        if payment_method.method == PaymentMethods.CARD:
            successful = payment_result.payment_status == PaymentStatus.SUCCEDED.value
            stored_order.payment_status = PaymentStatus.SUCCEDED if successful else PaymentStatus.FAILED
            if successful:
                card = payment_result.payment_method
                _enqueue_email(
                    session,
                    event_key=f"payment-confirmation:{payment_result.transaction_id}",
                    event_type="payment.card.succeeded",
                    payload={
                        "email": user.email,
                        "first_name": user.first_name,
                        "transaction_id": payment_result.transaction_id,
                        "amount": str(payment_result.transaction_amount),
                        "currency": payment_result.currency.value,
                        "created_at": payment_result.created_at.isoformat(),
                        "processing_network": card.processing_network,
                        "last_digits": card.last_digits,
                    },
                )
            else:
                stored_order.payment_failed_at = datetime.now(UTC)
                _enqueue_email(
                    session,
                    event_key=f"payment-failed:{payment_result.transaction_id}",
                    event_type="payment.card.failed",
                    payload={
                        "email": user.email,
                        "first_name": user.first_name,
                        "transaction_id": payment_result.transaction_id,
                        "amount": str(payment_result.transaction_amount),
                        "currency": payment_result.currency.value,
                        "message": payment_result.message or "El pago fue rechazado.",
                    },
                )
        else:
            _enqueue_email(
                session,
                event_key=f"cash-instructions:{order.id}",
                event_type="payment.cash.instructions",
                payload={
                    "email": user.email,
                    "first_name": user.first_name,
                    "order_id": order.id,
                    "amount": str(total),
                    "currency": "COP",
                    "street": address.street,
                    "details": address.details,
                    "city": address.city,
                },
            )

    loaded = await _load_order(session, order.id)
    message = (
        "Pago con tarjeta aprobado."
        if loaded.payment_status == PaymentStatus.SUCCEDED
        else "Pedido creado. Sigue las instrucciones de pago en efectivo."
        if loaded.payment_method == PaymentMethods.CASH
        else "El pago fue rechazado. El stock se liberará si continúa rechazado durante 10 minutos."
    )
    return CheckoutResponse(order=_order_response(loaded), message=message, transaction_id=loaded.payment_transaction_id)


@router.post("/orders/{order_id}/retry-payment", response_model=CheckoutResponse)
async def retry_uncertain_card_payment(
    order_id: int,
    payment_method: CardPaymentDataRequest,
    session: SessionDep,
    user: CurrentCustomer,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=255)],
    payment_factory=Depends(get_payment_method_factory),
) -> CheckoutResponse:
    order = await session.scalar(select(Order).where(Order.id == order_id))
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if order.payment_method != PaymentMethods.CARD or order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(status_code=409, detail="El pedido no tiene un pago con tarjeta pendiente de reconciliación.")
    if order.checkout_key != idempotency_key.strip():
        raise HTTPException(status_code=409, detail="Debes reutilizar el Idempotency-Key original del checkout.")
    total = order.total_price
    order_phone = order.phone_number
    user_first_name = user.first_name
    user_middle_name = user.middle_name
    user_first_surname = user.first_surname
    user_middle_surname = user.middle_surname
    user_email = user.email
    await session.rollback()

    user_data = UserDataRequest(
        first_name=user_first_name,
        middle_name=user_middle_name,
        first_surname=user_first_surname,
        middle_surname=user_middle_surname,
        contact_info=ContactInfoRequest(email=user_email, phone_number=order_phone),
    )
    payment_data = PaymentDataRequest(
        user_data=user_data,
        currency=TypeCurrency.COP,
        discount_type=DiscountStrategy.NODISCOUNT.value,
        transaction_amount=total,
        payment_method=payment_method,
        idempotency_key=idempotency_key.strip(),
    )
    try:
        processor = payment_factory.create_payment_processor(PaymentMethods.CARD)
        payment_result = await processor.process(payment_data)
    except Exception:
        logger.exception("Retry still has an uncertain Stripe outcome for order %s", order_id)
        raise HTTPException(
            status_code=503,
            detail=f"El resultado sigue sin confirmarse. El pedido {order_id} permanece pendiente; no crees otro pedido y reintenta con la misma clave.",
        ) from None

    async with session.begin():
        stored_order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
        if stored_order.payment_status == PaymentStatus.PENDING:
            stored_order.payment_transaction_id = payment_result.transaction_id
            if payment_result.payment_status == PaymentStatus.SUCCEDED.value:
                stored_order.payment_status = PaymentStatus.SUCCEDED
                stored_order.payment_failed_at = None
                card = payment_result.payment_method
                _enqueue_email(
                    session,
                    event_key=f"payment-confirmation:{payment_result.transaction_id}",
                    event_type="payment.card.succeeded",
                    payload={
                        "email": user_email,
                        "first_name": user_first_name,
                        "transaction_id": payment_result.transaction_id,
                        "amount": str(payment_result.transaction_amount),
                        "currency": payment_result.currency.value,
                        "created_at": payment_result.created_at.isoformat(),
                        "processing_network": card.processing_network,
                        "last_digits": card.last_digits,
                    },
                )
            else:
                stored_order.payment_status = PaymentStatus.FAILED
                stored_order.payment_failed_at = datetime.now(UTC)
                _enqueue_email(
                    session,
                    event_key=f"payment-failed:{payment_result.transaction_id}",
                    event_type="payment.card.failed",
                    payload={
                        "email": user_email,
                        "first_name": user_first_name,
                        "transaction_id": payment_result.transaction_id,
                        "amount": str(payment_result.transaction_amount),
                        "currency": payment_result.currency.value,
                        "message": payment_result.message or "El pago fue rechazado.",
                    },
                )

    loaded = await _load_order(session, order_id)
    message = "Pago con tarjeta aprobado." if loaded.payment_status == PaymentStatus.SUCCEDED else "El pago fue rechazado."
    return CheckoutResponse(order=_order_response(loaded), message=message, transaction_id=loaded.payment_transaction_id)


@router.get("/orders/me", response_model=list[OrderResponse])
async def order_history(session: SessionDep, user: CurrentCustomer) -> list[OrderResponse]:
    orders = (await session.scalars(
        select(Order).where(Order.user_id == user.id)
        .options(selectinload(Order.order_items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
    )).all()
    return [_order_response(order) for order in orders]


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def order_detail(
    order_id: int,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> OrderResponse:
    order = await _load_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if user.user_role == UserRole.CUSTOMER and order.user_id != user.id:
        raise HTTPException(status_code=403, detail="No puedes consultar un pedido de otro cliente.")
    if user.user_role not in {UserRole.CUSTOMER, UserRole.PACKAGING_MANAGER, UserRole.COURIER, UserRole.STORE_MANAGER, UserRole.WAREHOUSE_MANAGER}:
        raise HTTPException(status_code=403, detail="No tienes permisos.")
    return _order_response(order)


@router.get("/orders/{order_id}/receipt", response_model=ReceiptResponse)
async def digital_receipt(
    order_id: int,
    session: SessionDep,
    user: CurrentCustomer,
) -> ReceiptResponse:
    order = await _load_order(session, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if order.payment_method != PaymentMethods.CARD or order.payment_status != PaymentStatus.SUCCEDED or not order.payment_transaction_id:
        raise HTTPException(status_code=409, detail="El recibo solo está disponible para pagos con tarjeta aprobados.")
    return ReceiptResponse(
        receipt_number=f"REC-{order.id:08d}",
        issued_at=order.created_at,
        order=_order_response(order),
        payment_transaction_id=order.payment_transaction_id,
    )


@router.get("/operations/packaging", response_model=list[OrderResponse])
async def packaging_queue(session: SessionDep, user: PackagingManager) -> list[OrderResponse]:
    orders = (await session.scalars(
        select(Order).where(
            Order.delivery_status == DeliveryStatus.PENDING,
            or_(
                Order.payment_status == PaymentStatus.SUCCEDED,
                (Order.payment_method == PaymentMethods.CASH) & (Order.payment_status == PaymentStatus.PENDING),
            ),
        )
        .options(selectinload(Order.order_items).selectinload(OrderItem.product))
        .order_by(Order.created_at)
    )).all()
    return [_order_response(order) for order in orders]


@router.patch("/operations/orders/{order_id}/package", response_model=OrderResponse)
async def package_order(order_id: int, session: SessionDep, user: PackagingManager) -> OrderResponse:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if order.delivery_status != DeliveryStatus.PENDING or order.payment_status not in {PaymentStatus.SUCCEDED, PaymentStatus.PENDING}:
        raise HTTPException(status_code=409, detail="El pedido no está disponible para empaque.")
    order.delivery_status = DeliveryStatus.PACKAGED
    await session.commit()
    return _order_response(await _load_order(session, order_id))


@router.get("/operations/delivery", response_model=list[OrderResponse])
async def courier_queue(session: SessionDep, user: Courier) -> list[OrderResponse]:
    orders = (await session.scalars(
        select(Order).where(
            Order.delivery_status.in_([DeliveryStatus.PACKAGED, DeliveryStatus.IN_TRANSIT, DeliveryStatus.RETURNED_TO_WAREHOUSE]),
            or_(Order.courier_id.is_(None), Order.courier_id == user.id),
        ).options(selectinload(Order.order_items).selectinload(OrderItem.product))
        .order_by(Order.created_at)
    )).all()
    return [_order_response(order) for order in orders]


@router.patch("/operations/orders/{order_id}/pickup", response_model=OrderResponse)
async def pickup_order(order_id: int, session: SessionDep, user: Courier) -> OrderResponse:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if order.delivery_status not in {DeliveryStatus.PACKAGED, DeliveryStatus.RETURNED_TO_WAREHOUSE} or order.courier_id not in (None, user.id):
        raise HTTPException(status_code=409, detail="El pedido no está disponible para recoger.")
    if order.delivery_attempts >= 2:
        raise HTTPException(status_code=409, detail="El pedido agotó sus intentos de entrega.")
    order.courier_id = user.id
    order.delivery_attempts += 1
    order.delivery_status = DeliveryStatus.IN_TRANSIT
    await session.commit()
    return _order_response(await _load_order(session, order_id))


@router.patch("/operations/orders/{order_id}/payment", response_model=OrderResponse)
async def confirm_cash_payment(order_id: int, session: SessionDep, user: Courier) -> OrderResponse:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if order.courier_id != user.id or order.delivery_status != DeliveryStatus.IN_TRANSIT:
        raise HTTPException(status_code=409, detail="Solo puedes actualizar pedidos asignados y en camino.")
    if order.payment_method != PaymentMethods.CASH or order.payment_status != PaymentStatus.PENDING:
        raise HTTPException(status_code=409, detail="Solo se puede confirmar el pago pendiente de pedidos en efectivo.")
    order.payment_status = PaymentStatus.SUCCEDED
    await session.commit()
    return _order_response(await _load_order(session, order_id))


@router.patch("/operations/orders/{order_id}/delivery", response_model=OrderResponse)
async def confirm_delivery(
    order_id: int,
    session: SessionDep,
    user: Courier,
    outcome: str = Query(default="delivered", pattern="^(delivered|customer_canceled|not_received)$"),
) -> OrderResponse:
    order = await session.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado.")
    if order.courier_id != user.id or order.delivery_status != DeliveryStatus.IN_TRANSIT:
        raise HTTPException(status_code=409, detail="Solo puedes cerrar pedidos asignados y en camino.")
    if outcome == "delivered" and order.payment_method == PaymentMethods.CASH and order.payment_status != PaymentStatus.SUCCEDED:
        raise HTTPException(status_code=409, detail="Confirma primero la recepción del pago en efectivo.")
    if outcome == "delivered":
        order.delivery_status = DeliveryStatus.DELIVERED
    elif outcome == "customer_canceled":
        order.delivery_status = DeliveryStatus.CANCELED
    elif order.delivery_attempts < 2:
        order.delivery_status = DeliveryStatus.RETURNED_TO_WAREHOUSE
    else:
        order.delivery_status = DeliveryStatus.CANCELED
    await session.commit()
    return _order_response(await _load_order(session, order_id))



@router.post("/products/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    session: SessionDep,
    user: StoreManager,
    file: UploadFile = File(...),
) -> ProductResponse:
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    extension = allowed_types.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Formato no permitido. Usa JPG, PNG o WEBP.")
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="La imagen no puede superar 5 MB.")
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    media_root = Path(os.getenv("PRODUCT_IMAGE_DIR", "media/products")).resolve()
    await asyncio.to_thread(media_root.mkdir, parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    destination = media_root / filename
    await asyncio.to_thread(destination.write_bytes, content)
    product.image_path = f"/media/products/{filename}"
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)
