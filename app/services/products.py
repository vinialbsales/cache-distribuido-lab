import json
import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.cache_metrics import cache_metrics

logger = logging.getLogger(__name__)


def product_cache_key(product_id: int) -> str:
    return f"product:{product_id}"


async def get_product_from_db(session: AsyncSession, product_id: int) -> Product | None:
    return await session.get(Product, product_id)


def serialize_product(product: Product) -> str:
    product_read = ProductRead.model_validate(product)
    return product_read.model_dump_json()


def deserialize_product(payload: str) -> ProductRead:
    return ProductRead.model_validate(json.loads(payload))


async def get_product_with_cache(
    session: AsyncSession,
    redis: Redis,
    product_id: int,
) -> tuple[ProductRead | None, str]:
    key = product_cache_key(product_id)
    cached_product = await redis.get(key)

    if cached_product is not None:
        logger.info("CACHE HIT %s", key)
        cache_metrics.register_hit()
        return deserialize_product(cached_product), "HIT"

    logger.info("CACHE MISS %s", key)
    cache_metrics.register_miss()
    logger.info("DB QUERY %s", key)
    product = await get_product_from_db(session, product_id)
    if product is None:
        return None, "MISS"

    ttl_seconds = get_settings().redis_ttl_seconds
    await redis.set(key, serialize_product(product), ex=ttl_seconds)
    logger.info("REDIS SET %s", key)
    return ProductRead.model_validate(product), "MISS"


async def invalidate_product_cache(redis: Redis, product_id: int) -> None:
    key = product_cache_key(product_id)
    await redis.delete(key)
    logger.info("CACHE INVALIDATE %s", key)


async def create_product(session: AsyncSession, product_data: ProductCreate) -> Product:
    product = Product(**product_data.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def update_product(
    session: AsyncSession,
    redis: Redis,
    product_id: int,
    product_data: ProductUpdate,
) -> Product | None:
    product = await get_product_from_db(session, product_id)
    if product is None:
        return None

    for field, value in product_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await session.commit()
    await session.refresh(product)
    await invalidate_product_cache(redis, product_id)
    return product


async def delete_product(
    session: AsyncSession,
    redis: Redis,
    product_id: int,
) -> bool:
    product = await get_product_from_db(session, product_id)
    if product is None:
        return False

    await session.delete(product)
    await session.commit()
    await invalidate_product_cache(redis, product_id)
    return True


async def create_product_write_through(
    session: AsyncSession,
    redis: Redis,
    product_data: ProductCreate,
) -> ProductRead:
    product = await create_product(session, product_data)
    key = product_cache_key(product.id)
    ttl_seconds = get_settings().redis_ttl_seconds
    await redis.set(key, serialize_product(product), ex=ttl_seconds)
    logger.info("REDIS SET %s", key)
    return ProductRead.model_validate(product)
