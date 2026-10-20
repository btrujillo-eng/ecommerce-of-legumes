from fastapi import FastAPI

from app.api.v1.routers import health, payment, user_auth, user_registration

app = FastAPI(
    title="E-commerce of legumes",
    version="1.0.0"
)

app.include_router(payment.router)
app.include_router(health.router)
app.include_router(user_registration.router)
app.include_router(user_auth.router_login)
app.include_router(user_auth.router_home_page)