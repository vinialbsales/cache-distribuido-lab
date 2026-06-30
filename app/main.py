from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import logging

from fastapi import Depends, FastAPI, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.redis import create_redis_client, get_redis
from app.db.seed import seed_initial_products
from app.db.session import async_session_factory, close_database, engine, get_session
from app.models import Product  # noqa: F401
from app.schemas.product import (
    CacheMetricsRead,
    ProductCacheRead,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)
from app.services.cache_metrics import cache_metrics
from app.services.products import (
    create_product_write_through,
    delete_product,
    get_product_from_db,
    get_product_with_cache,
    update_product,
)


def configure_logging() -> None:
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)

    uvicorn_logger = logging.getLogger("uvicorn.error")
    if uvicorn_logger.handlers:
        app_logger.handlers = uvicorn_logger.handlers
        app_logger.propagate = False
    else:
        logging.basicConfig(level=logging.INFO)
        app_logger.propagate = True


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()

    redis_client = create_redis_client()
    app.state.redis = redis_client

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        await seed_initial_products(session)

    try:
        yield
    finally:
        await redis_client.aclose()
        await close_database()


app = FastAPI(
    title="cache-distribuido-lab",
    description="API acadêmica para demonstrar estratégias de cache distribuído com Redis e PostgreSQL.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/products/{product_id}/no-cache", response_model=ProductRead)
async def get_product_no_cache(
    product_id: int,
    session: AsyncSession = Depends(get_session),
) -> Product:
    product = await get_product_from_db(session, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/products/{product_id}/cache", response_model=ProductCacheRead)
async def get_product_cache(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, str | ProductRead]:
    product, cache_status = await get_product_with_cache(session, redis, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"cache_status": cache_status, "product": product}


@app.put("/products/{product_id}", response_model=ProductRead)
async def put_product(
    product_id: int,
    product_data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> Product:
    product = await update_product(session, redis, product_id, product_data)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> Response:
    deleted = await delete_product(session, redis, product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/products/write-through", response_model=ProductCacheRead)
async def post_product_write_through(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict[str, str | ProductRead]:
    product = await create_product_write_through(session, redis, product_data)
    return {"cache_status": "WRITE_THROUGH", "product": product}


@app.get("/metrics/cache", response_model=CacheMetricsRead)
async def get_cache_metrics() -> dict[str, int | float]:
    return cache_metrics.snapshot()
