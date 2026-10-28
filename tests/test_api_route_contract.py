import xml.etree.ElementTree as ET
from pathlib import Path

from main import app


def test_required_workbook_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}
    expected = {
        "/register/user/",
        "/users/v1/auth/token",
        "/users/v1/auth/password-reset/request",
        "/users/v1/auth/password-reset/confirm",
        "/products",
        "/products/{product_id}/stock",
        "/products/{product_id}/price",
        "/products/{product_id}/image",
        "/cart",
        "/cart/items",
        "/cart/items/{product_id}",
        "/checkout",
        "/orders/me",
        "/orders/{order_id}",
        "/orders/{order_id}/receipt",
        "/orders/{order_id}/retry-payment",
        "/operations/packaging",
        "/operations/orders/{order_id}/package",
        "/operations/delivery",
        "/operations/orders/{order_id}/pickup",
        "/operations/orders/{order_id}/payment",
        "/operations/orders/{order_id}/delivery",
    }
    assert expected.issubset(paths)


def test_openapi_schema_can_be_generated() -> None:
    schema = app.openapi()
    assert "/checkout" in schema["paths"]
    assert "/orders/{order_id}/retry-payment" in schema["paths"]


def test_jmeter_performance_plan_is_valid_xml() -> None:
    plan = Path("tests/performance/registration-login-60-users.jmx")
    root = ET.parse(plan).getroot()
    assert root.tag == "jmeterTestPlan"
