from abc import ABC, abstractmethod
from decimal import Decimal

from app.infrastructure.dtos import (
    RegisteredProduct,
    RegisterProductData,
    UpdatedProduct,
)


class IProductRepository(ABC):
    @abstractmethod
    async def get_product_by_id(self, product_id: int) -> RegisterProductData | None: ...
    
    @abstractmethod
    async def get_product_by_name(self, name: str) -> RegisterProductData | None: ...
    
    @abstractmethod
    async def add_product(self, product_data: RegisterProductData) -> RegisteredProduct: ...
    
    @abstractmethod
    async def update_price(self, product_id: int, new_price: Decimal) -> UpdatedProduct: ...
    
    @abstractmethod
    async def update_stock(self, product_id: int, new_stock: int) -> UpdatedProduct: ...