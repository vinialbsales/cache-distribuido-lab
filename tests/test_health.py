import pytest
from fastapi.testclient import TestClient
from redis import Redis, from_url

from app.core.config import get_settings
from app.main import app
from app.services.cache_metrics import cache_metrics


@pytest.fixture(name="redis_client")
def redis_client_fixture() -> Redis:
    redis = from_url(get_settings().redis_url, decode_responses=True)
    redis.flushdb()
    yield redis
    redis.flushdb()
    redis.close()


@pytest.fixture(name="client")
def client_fixture(redis_client: Redis) -> TestClient:
    cache_metrics.reset()

    with TestClient(app) as client:
        yield client


def product_payload(name: str = "Produto Teste") -> dict[str, str | int]:
    return {
        "name": name,
        "description": "Criado por teste automatizado.",
        "price": "99.90",
        "stock": 7,
    }


def create_write_through_product(
    client: TestClient,
    name: str = "Produto Teste",
) -> dict:
    response = client.post("/products/write-through", json=product_payload(name))
    assert response.status_code == 200
    body = response.json()
    assert body["cache_status"] == "WRITE_THROUGH"
    return body["product"]


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_product_no_cache(client: TestClient) -> None:
    response = client.get("/products/1/no-cache")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["name"]
    assert "cache_status" not in body


def test_first_cached_product_request_generates_miss(client: TestClient) -> None:
    response = client.get("/products/1/cache")

    assert response.status_code == 200
    body = response.json()
    assert body["cache_status"] == "MISS"
    assert body["product"]["id"] == 1

    metrics = client.get("/metrics/cache").json()
    assert metrics["hits"] == 0
    assert metrics["misses"] == 1
    assert metrics["total"] == 1
    assert metrics["hit_rate_percent"] == 0.0


def test_second_cached_product_request_generates_hit(client: TestClient) -> None:
    first_response = client.get("/products/1/cache")
    second_response = client.get("/products/1/cache")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["cache_status"] == "MISS"
    assert second_response.json()["cache_status"] == "HIT"
    assert second_response.json()["product"]["id"] == 1


def test_cache_metrics_returns_coherent_values(client: TestClient) -> None:
    client.get("/products/1/cache")
    client.get("/products/1/cache")

    response = client.get("/metrics/cache")

    assert response.status_code == 200
    metrics = response.json()
    assert metrics["hits"] == 1
    assert metrics["misses"] == 1
    assert metrics["total"] == metrics["hits"] + metrics["misses"]
    assert metrics["hit_rate_percent"] == 50.0


def test_put_invalidates_old_cache(
    client: TestClient,
    redis_client: Redis,
) -> None:
    product = create_write_through_product(client, "Produto Cache Antigo")
    product_id = product["id"]
    cache_key = f"product:{product_id}"
    assert redis_client.exists(cache_key) == 1

    response = client.put(
        f"/products/{product_id}",
        json={"name": "Produto Atualizado"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Produto Atualizado"
    assert redis_client.get(cache_key) is None


def test_after_put_next_cached_read_generates_miss_and_returns_updated_data(
    client: TestClient,
) -> None:
    product = create_write_through_product(client, "Produto Antes do PUT")
    product_id = product["id"]

    update_response = client.put(
        f"/products/{product_id}",
        json={"name": "Produto Depois do PUT", "stock": 11},
    )
    assert update_response.status_code == 200

    response = client.get(f"/products/{product_id}/cache")

    assert response.status_code == 200
    body = response.json()
    assert body["cache_status"] == "MISS"
    assert body["product"]["name"] == "Produto Depois do PUT"
    assert body["product"]["stock"] == 11


def test_post_write_through_creates_product_and_writes_to_redis(
    client: TestClient,
    redis_client: Redis,
) -> None:
    response = client.post(
        "/products/write-through",
        json=product_payload("Produto Write Through"),
    )

    assert response.status_code == 200
    body = response.json()
    product = body["product"]
    cache_key = f"product:{product['id']}"
    cached_product = redis_client.get(cache_key)

    assert body["cache_status"] == "WRITE_THROUGH"
    assert product["name"] == "Produto Write Through"
    assert cached_product is not None
    assert "Produto Write Through" in cached_product


def test_delete_invalidates_cache(
    client: TestClient,
    redis_client: Redis,
) -> None:
    product = create_write_through_product(client, "Produto Para Deletar")
    product_id = product["id"]
    cache_key = f"product:{product_id}"
    assert redis_client.exists(cache_key) == 1

    response = client.delete(f"/products/{product_id}")

    assert response.status_code == 204
    assert redis_client.get(cache_key) is None


def test_delete_makes_product_stop_being_returned(client: TestClient) -> None:
    product = create_write_through_product(client, "Produto Removido")
    product_id = product["id"]

    delete_response = client.delete(f"/products/{product_id}")
    no_cache_response = client.get(f"/products/{product_id}/no-cache")
    cache_response = client.get(f"/products/{product_id}/cache")

    assert delete_response.status_code == 204
    assert no_cache_response.status_code == 404
    assert cache_response.status_code == 404
