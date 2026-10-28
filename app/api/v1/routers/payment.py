from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", deprecated=True)
async def reject_legacy_direct_payment() -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Este endpoint fue retirado porque permitía cobrar sin validar carrito, stock y pedido. Usa POST /checkout.",
    )
