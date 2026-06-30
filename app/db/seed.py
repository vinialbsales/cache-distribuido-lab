from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product

INITIAL_PRODUCTS = (
    {
        "name": "Notebook Academico",
        "description": "Produto inicial para testes sem cache e com cache.",
        "price": Decimal("4299.90"),
        "stock": 10,
    },
    {
        "name": "Monitor 27 Pol",
        "description": "Carga inicial para benchmark k6.",
        "price": Decimal("1499.00"),
        "stock": 15,
    },
    {
        "name": "Teclado Mecanico",
        "description": "Item usado em cenarios de leitura repetida.",
        "price": Decimal("399.90"),
        "stock": 30,
    },
)


async def seed_initial_products(session: AsyncSession) -> None:
    total_products = await session.scalar(select(func.count(Product.id)))
    if total_products:
        return

    session.add_all(Product(**product) for product in INITIAL_PRODUCTS)
    await session.commit()
