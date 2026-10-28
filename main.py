import asyncio
import os
from pathlib import Path
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers import health, payment, password_reset, user_auth, user_registration
from app.api.v1.routers.commerce import router as commerce_router
from app.infrastructure.config import get_settings
from app.infrastructure.database_engine import AsyncSessionLocal, engine
from app.infrastructure.notifications.payment_outbox_worker import PaymentOutboxWorker


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    worker = PaymentOutboxWorker(AsyncSessionLocal, get_settings())
    task = asyncio.create_task(worker.run(), name="payment-outbox-worker")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await engine.dispose()


app = FastAPI(title="E-commerce of legumes", version="1.0.0", lifespan=lifespan)
app.include_router(payment.router)
app.include_router(health.router)
app.include_router(user_registration.router)
app.include_router(user_auth.router_login)
app.include_router(user_auth.router_home_page)
app.include_router(password_reset.router)
app.include_router(commerce_router)
media_root = Path(os.getenv("PRODUCT_IMAGE_DIR", "media/products")).resolve()
media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media/products", StaticFiles(directory=str(media_root)), name="product-images")
