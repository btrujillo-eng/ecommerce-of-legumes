import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports import IProductRepository
from app.exceptions import (
    ProductAlreadyExistsError,
    ProductDoesNotExistError,
    ProductRegistrationServiceError,
)
from app.infrastructure.dtos import (
    RegisteredProduct,
    RegisterProductData,
    UpdatedProduct,
)
from app.infrastructure.persistence.models import Product

logger = logging.getLogger(__name__)

class ProductRepository(IProductRepository):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session
        
    def _to_product_data(self, product: Product) -> RegisterProductData:
        return RegisterProductData(
            product_name=product.name,
            section_id=product.section_id,
            price=product.price,
            stock=product.stock,
            unit_of_measure=product.unit_of_measure
        )
        
    async def _get_product(self, product_id: int) -> Product:
        stmt = select(Product).where(Product.id == product_id)
        result = await self.db_session.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise ProductDoesNotExistError("The product does not exist in the system")
        
        return product
    
    def _to_updated_product(self, product_data: Product) -> UpdatedProduct:
        return UpdatedProduct(
            id=product_data.id,
            name=product_data.name,
            price=product_data.price,
            stock=product_data.stock,
            unit_of_measure=product_data.unit_of_measure
        )
        
    async def get_product_by_id(self, product_id: int) -> RegisterProductData | None:
        stmt = select(Product).where(Product.id == product_id)
        product = await self.db_session.scalar(stmt)
        if product is None:
            return None
        
        return self._to_product_data(product)
    
    async def get_product_by_name(self, name: str) -> RegisterProductData | None:
        stmt = select(Product).where(Product.name == name)
        product = await self.db_session.scalar(stmt)
        if product is None:
            return None
        
        return self._to_product_data(product)
    
    async def add_product(self, product_data: RegisterProductData) -> RegisteredProduct:
        product = Product(
            name=product_data.product_name,
            section_id= product_data.section_id,
            price=product_data.price,
            unit_of_measure=product_data.unit_of_measure,
            stock=product_data.stock
        )
        try:
            self.db_session.add(product)
            await self.db_session.flush()
            await self.db_session.refresh(product)
            return RegisteredProduct(
                id=product.id,
                product_name=product.name,
                section_id=product.section_id,
                price=product.price,
                stock=product.stock,
                unit_of_measure=product.unit_of_measure
            )
        except IntegrityError as e:
            sqlstate = getattr(e.orig, "sqlstate", None) or getattr(e.orig, "pgcode", None)
            if sqlstate == "23505":
                raise ProductAlreadyExistsError("The product already exist in the system.")
            
            logger.critical("Crital error in ProductRepository.add_product", exc_info=e)
            raise ProductRegistrationServiceError("Product registration service unavailable")
        
    async def update_price(self, product_id: int, new_price: Decimal) -> UpdatedProduct:
        product = await self._get_product(product_id)
        product.price = new_price
        await self.db_session.flush()
        return self._to_updated_product(product)
        
    async def update_stock(self, product_id: int, new_stock: int) -> UpdatedProduct:
        product = await self._get_product(product_id)
        product.stock = new_stock
        await self.db_session.flush()
        return self._to_updated_product(product)