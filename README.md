# cache-distribuido-lab

Projeto acadêmico para demonstrar estratégias de caching distribuído usando Redis como cache e PostgreSQL como banco principal.

## Objetivo

Implementar uma API com FastAPI que permita comparar consultas diretas ao PostgreSQL com consultas usando cache distribuído no Redis.

## Arquitetura Inicial

- **FastAPI**: API HTTP da aplicação.
- **PostgreSQL**: banco principal e fonte de verdade dos produtos.
- **Redis**: cache distribuído para reduzir latência e carga no banco.
- **Docker Compose**: orquestra API, PostgreSQL e Redis localmente.
- **pytest**: testes automatizados.
- **k6**: testes de carga para comparar endpoints com cache e sem cache.

## Endpoints implementados

### Healthcheck

```bash
curl http://localhost:8000/health
```

### Consulta sem cache

Consulta diretamente o PostgreSQL.

```bash
curl http://localhost:8000/products/1/no-cache
```

### Consulta com cache-aside

Usa a chave Redis `product:{id}`. A primeira chamada consulta o PostgreSQL, grava no Redis com TTL e retorna `cache_status` como `MISS`. A segunda chamada para o mesmo produto retorna `cache_status` como `HIT`. Os logs registram `CACHE MISS product:{id}`, `DB QUERY product:{id}`, `REDIS SET product:{id}` e `CACHE HIT product:{id}`.

```bash
curl http://localhost:8000/products/1/cache
curl http://localhost:8000/products/1/cache
```

### Atualização com invalidação de cache

Atualiza o produto no PostgreSQL e remove a chave Redis `product:{id}`. Isso evita que uma leitura cacheada continue retornando dados antigos. A próxima chamada para `GET /products/{id}/cache` gera `MISS`, consulta o banco e recria o cache com os dados atualizados.

```bash
curl -X PUT http://localhost:8000/products/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Notebook Atualizado","price":"4399.90","stock":8}'
```

### Remoção com invalidação de cache

Remove o produto no PostgreSQL e invalida a chave Redis `product:{id}`.

```bash
curl -X DELETE http://localhost:8000/products/1
```

### Escrita write-through

Cria o produto no PostgreSQL e grava imediatamente o mesmo produto no Redis. A resposta retorna `cache_status` como `WRITE_THROUGH`.

```bash
curl -X POST http://localhost:8000/products/write-through \
  -H "Content-Type: application/json" \
  -d '{"name":"Mouse Sem Fio","description":"Produto criado com write-through","price":"199.90","stock":20}'
```

### Métricas de cache

```bash
curl http://localhost:8000/metrics/cache
```

Resposta esperada:

```json
{
  "hits": 1,
  "misses": 1,
  "total": 2,
  "hit_rate_percent": 50.0
}
```

## Estratégias que serão demonstradas

### Cache-aside

O endpoint `GET /products/{id}/cache` consulta primeiro o Redis. Em caso de cache hit, retorna o dado do cache. Em caso de cache miss, consulta o PostgreSQL, grava o resultado no Redis com TTL e retorna o produto.

### Write-through

O endpoint `POST /products/write-through` grava o produto no PostgreSQL e também atualiza o Redis no mesmo fluxo de escrita. A vantagem é que a próxima leitura cacheada já encontra o produto no Redis. O custo é que a escrita fica acoplada ao cache: além de persistir no banco, ela também precisa atualizar o Redis.

### Invalidação

Os endpoints `PUT /products/{id}` e `DELETE /products/{id}` removem a chave `product:{id}` do Redis depois de alterar o PostgreSQL. A invalidação mantém o PostgreSQL como fonte de verdade e impede que dados obsoletos sejam servidos pelo cache.

### Diferença entre cache-aside e write-through

No cache-aside, o cache é preenchido durante a leitura: a aplicação tenta ler do Redis, consulta o PostgreSQL quando há miss e então salva o resultado no Redis. No write-through, o cache é preenchido durante a escrita: a aplicação grava no PostgreSQL e atualiza o Redis imediatamente no mesmo fluxo.

## Estrutura de Pastas

```text
.
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── docker/
│   └── postgres/
│       └── init.sql
├── k6/
│   ├── cache_cold.js
│   ├── cache_hot.js
│   ├── mixed_load.js
│   └── no_cache.js
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── TODO.md
```

## Como executar

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Suba os serviços:

```bash
docker compose up --build -d
```

Verifique a API:

```bash
curl http://localhost:8000/health
```

## Testes

Os testes automatizados cobrem healthcheck, busca sem cache, cache miss, cache hit, métricas, invalidação após `PUT`, write-through e remoção com invalidação.

```bash
docker compose exec api pytest
```

Validações úteis:

```bash
python -m compileall app
docker compose config
```

## Benchmark

Os scripts k6 medem as métricas padrão `http_req_duration`, `http_req_failed` e `http_reqs`. No resumo final do k6, use:

- `http_req_duration avg`: latência média;
- `http_req_duration p(95)`: p95;
- `http_reqs rate`: requisições por segundo;
- `http_req_failed rate`: taxa de falhas.

Suba os containers:

```bash
docker compose up --build -d
```

Limpe o Redis antes de cenários frios:

```bash
docker compose exec redis redis-cli FLUSHDB
```

Aqueça o cache manualmente quando quiser medir cache quente:

```bash
curl http://localhost:8000/products/1/cache
curl http://localhost:8000/products/1/cache
```

Rode o benchmark sem cache:

```bash
k6 run k6/no_cache.js
```

Rode o benchmark com cache frio, depois de limpar o Redis:

```bash
docker compose exec redis redis-cli FLUSHDB
k6 run k6/cache_cold.js
```

Rode o benchmark com cache quente:

```bash
docker compose exec redis redis-cli FLUSHDB
curl http://localhost:8000/products/1/cache
k6 run k6/cache_hot.js
```

Rode uma carga mista com leituras cacheadas, leituras sem cache e algumas atualizações:

```bash
k6 run k6/mixed_load.js
```

Também é possível rodar k6 via Docker Compose, sem instalar k6 localmente:

```bash
docker compose --profile benchmark run --rm k6 run /scripts/no_cache.js
docker compose --profile benchmark run --rm k6 run /scripts/cache_hot.js
docker compose --profile benchmark run --rm k6 run /scripts/mixed_load.js
```

Os parâmetros podem ser ajustados por variáveis de ambiente:

```bash
VUS=50 DURATION=1m PRODUCT_ID=1 k6 run k6/cache_hot.js
```

## Interpretação dos resultados

Compare os cenários usando a tabela abaixo:

| Cenário | Latência média | p95 | Requisições por segundo | Observação |
| --- | --- | --- | --- | --- |
| Sem cache | 13.95 ms | 27.06 ms | 19.65 req/s | 0% de falhas |
| Cache frio | 5.70 ms | 5.70 ms | N/A | 0% de falhas; apenas 1 iteração, usada para demonstrar `MISS` |
| Cache quente | 2.32 ms | 3.96 ms | 19.97 req/s | 0% de falhas |
| Carga mista | 6.13 ms | 33.04 ms | 19.84 req/s | 0% de falhas |

O cenário sem cache consulta o PostgreSQL diretamente em todas as leituras. Com cache quente, as leituras são atendidas pelo Redis, reduzindo a latência média de 13.95 ms para 2.32 ms, uma queda de aproximadamente 83%. O p95 também caiu de 27.06 ms para 3.96 ms, uma redução de aproximadamente 85%. O cache frio foi executado com apenas 1 iteração para demonstrar o comportamento de `MISS`: a aplicação consulta o banco, popula o Redis e deixa o dado pronto para leituras seguintes.

O throughput ficou parecido entre os cenários principais: 19.65 req/s sem cache, 19.97 req/s com cache quente e 19.84 req/s na carga mista. Isso acontece porque os scripts de benchmark usam pausa entre iterações, o que limita a taxa de requisições gerada pelo teste. Por isso, a comparação principal deve ser feita pela latência média e pelo p95, não pela vazão.

A comparação principal deve observar:

- latência média e percentis (`http_req_duration`);
- quantidade de requisições por segundo como métrica secundária;
- diferença entre cache hit e cache miss;
- redução de consultas ao PostgreSQL quando o Redis atende as leituras.

## Status

A aplicação já contém a base FastAPI, integração com PostgreSQL e Redis, endpoints de leitura sem cache, leitura com cache-aside, métricas em memória, invalidação de cache em atualização/remoção e criação write-through. As próximas etapas estão descritas no [TODO.md](TODO.md).
