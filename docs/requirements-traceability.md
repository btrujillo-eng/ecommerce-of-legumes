# Matriz de implementación — requisitos hasta «7. Mockups»

Alcance tomado de `Ciclo_Vida_Software_Aseguramiento_Calidad_UNIMINUTO.xlsx`: hojas `Instrucciones`, `1. Proyecto`, `2. Interesados`, `3. Req Funcionales`, `4. Req No Funcionales`, `5. Historias de Usuario`, `6. Casos de Uso` y `7. Mockups`. Las hojas posteriores no se consideran alcance de esta entrega.

## Requisitos funcionales

| ID | Funcionalidad | Endpoint / componente |
|---|---|---|
| RF-0001 | Registro | `POST /register/user/`; crea siempre rol `customer`, contraseña fuerte y hash en persistencia |
| RF-0002 | Autenticación | `POST /users/v1/auth/token`; JWT Bearer |
| RF-0003 | Restaurar contraseña | `POST /users/v1/auth/password-reset/request`, `POST /users/v1/auth/password-reset/confirm`; código de 4 dígitos, 10 min, máximo 5 intentos, uso único |
| RF-0004 | Búsqueda de catálogo | `GET /products?q=...`; busca nombre o sección y valida el texto |
| RF-0005 | Agregar al carrito | `POST /cart/items`; cantidad positiva y validación de stock |
| RF-0006 | Total del carrito | `GET /cart` y respuesta de `POST /cart/items`; total calculado desde precios persistidos |
| RF-0007 | Eliminar del carrito | `DELETE /cart/items/{product_id}` |
| RF-0008 | Domicilio de entrega | `POST /checkout`; valida calle, detalles, ciudad y teléfono |
| RF-0009 | Actualizar stock | `PATCH /products/{product_id}/stock`; rol `warehouse_manager` |
| RF-0010 | Actualizar precio | `PATCH /products/{product_id}/price`; rol `store_manager` |
| RF-0011 | Procesar pedido/pago | `POST /checkout`; mínimo $20.000 COP, reserva de stock, tarjeta Stripe o efectivo; requiere `Idempotency-Key` |
| RF-0011 (reconciliación) | Reintentar resultado incierto de Stripe | `POST /orders/{order_id}/retry-payment`; mismo propietario y clave original, reutiliza idempotencia de Stripe |
| RF-0012 | Recibo digital | `GET /orders/{order_id}/receipt`; solo tarjeta aprobada |
| RF-0013 | Historial y detalle | `GET /orders/me`, `GET /orders/{order_id}`; aislamiento de pedidos del cliente |
| RF-0014 | Cola de empaque | `GET /operations/packaging`; rol `packaging_manager` |
| RF-0015 | Confirmar empaque | `PATCH /operations/orders/{order_id}/package` |
| RF-0016 | Confirmar pago en efectivo | `PATCH /operations/orders/{order_id}/payment`; rol domiciliario y pedido asignado/en camino |
| RF-0017 | Recogida y entrega | `GET /operations/delivery`, `PATCH /operations/orders/{order_id}/pickup`, `PATCH /operations/orders/{order_id}/delivery`; máximo dos intentos |
| RF-0018 | Registrar producto | `POST /products`; rol `store_manager`; imagen local mediante `POST /products/{product_id}/image` |

## Requisitos no funcionales y verificación

- RNF-0001/RNF-0005: objetivos de p95 ≤ 3 s para registro e inicio de sesión bajo 60 usuarios concurrentes. Deben medirse en un entorno con PostgreSQL de pruebas y credenciales de prueba.
- RNF-0002/RNF-0003: hash de contraseña y validación de credenciales. La API no permite que el usuario elija su rol al registrarse.
- RNF-0004: SQLAlchemy parametriza consultas; la búsqueda rechaza entradas fuera del patrón esperado.
- RNF-0007: código de restauración verificado contra hash, expira a los 10 minutos, máximo cinco intentos y uso único.
- RNF-0010: pruebas de validación del carrito; el total usa precios de base de datos, no precios enviados por el cliente.
- RNF-0013/RNF-0014/RNF-0015/RNF-0016/RNF-0019/RNF-0020/RNF-0021/RNF-0022: ejecutar pruebas de rendimiento con JMeter o pytest en entorno de prueba y comparar con los límites de la hoja Excel (3–7 s según operación).
- RNF-0006/RNF-0008/RNF-0009/RNF-0011/RNF-0012/RNF-0017/RNF-0018: son métricas de usabilidad de interfaz (Cypress); requieren el frontend conectado a estos endpoints.
- RNF-0023: routers, esquemas, modelos, persistencia y worker se mantienen en módulos separados.

El endpoint legado `POST /payments/` retorna HTTP 410 porque permitía procesar cobros sin validar carrito, stock ni persistencia del pedido. Los pagos deben pasar por `POST /checkout` con el encabezado `Idempotency-Key` (16–255 caracteres) para proteger los reintentos.

## Flujo de notificación y consistencia

Las confirmaciones de tarjeta aprobada, tarjeta rechazada e instrucciones de efectivo se guardan en `outbox_events` y se envían por Resend mediante un worker. Si Stripe devuelve un error de red/API cuyo resultado no puede confirmarse, el pedido permanece pendiente y no se libera el stock automáticamente; el cliente puede reintentar con la misma clave o debe reconciliarse mediante Stripe. Hay reintentos exponenciales y un límite de ocho intentos. Los pagos con tarjeta rechazados que continúen rechazados durante 10 minutos cancelan el pedido y devuelven las cantidades reservadas al stock.

## Pruebas de rendimiento

El plan JMeter `tests/performance/registration-login-60-users.jmx` ejecuta registro e inicio de sesión con 60 usuarios concurrentes y correos únicos. Ejecuta en un entorno de pruebas, no en producción:

```bash
for run in 1 2 3; do
  jmeter -n -t tests/performance/registration-login-60-users.jmx -l "results-$run.jtl" -e -o "report-$run"
done
```

El plan apunta por defecto a `http://127.0.0.1:8000`; cambia el host/puerto en el archivo si el entorno es diferente. Revisa el percentil 95 de cada sampler y exige ≤ 3 s. Los objetivos de stock, precio, checkout, recibo, empaque, pago y entrega requieren escenarios con productos y usuarios de cada rol sembrados en el entorno de prueba; no se consideran aprobados solo por existir el endpoint.

## Imágenes de producto

Las imágenes se reciben mediante `POST /products/{product_id}/image`, se limitan a 5 MB y a JPG/PNG/WEBP, y se guardan bajo `PRODUCT_IMAGE_DIR` (por defecto `media/products`). En contenedores, monta un volumen persistente en esa ruta y define `PRODUCT_IMAGE_DIR=/app/media/products`.

## Aplicación

Antes de ejecutar la aplicación en un entorno nuevo, configurar las variables requeridas en `.env`, aplicar `alembic upgrade head` y ejecutar `pytest`. La implementación remota no se considera validada hasta que pasen las pruebas y se midan los RNF en el entorno objetivo.
