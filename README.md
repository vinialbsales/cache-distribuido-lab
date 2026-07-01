# cache-distribuido-lab

Projeto acadêmico para demonstrar estratégias de caching distribuído usando Redis como cache e PostgreSQL como banco principal.

## Objetivo

Implementar uma API com FastAPI que permita comparar consultas diretas ao PostgreSQL com consultas usando cache distribuído no Redis.

## Arquitetura

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

## Estratégias demonstradas

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
├── results/
│   ├── cache_cold.json
│   ├── cache_hot.json
│   ├── mixed_load.json
│   └── no_cache.json
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

Para atualizar os arquivos usados na tabela deste README, exporte o resumo do k6:

```bash
k6 run --summary-export results/no_cache.json k6/no_cache.js
docker compose exec redis redis-cli FLUSHDB
k6 run --summary-export results/cache_cold.json k6/cache_cold.js
docker compose exec redis redis-cli FLUSHDB
k6 run --summary-export results/cache_hot.json k6/cache_hot.js
k6 run --summary-export results/mixed_load.json k6/mixed_load.js
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
docker compose --profile benchmark run --rm k6 run /scripts/cache_cold.js
docker compose --profile benchmark run --rm k6 run /scripts/cache_hot.js
docker compose --profile benchmark run --rm k6 run /scripts/mixed_load.js
```

Os parâmetros podem ser ajustados por variáveis de ambiente. Ao rodar k6 localmente, use os nomes lidos diretamente pelos scripts:

```bash
VUS=50 DURATION=1m PRODUCT_ID=1 k6 run k6/cache_hot.js
```

Ao rodar pelo serviço `k6` do Docker Compose, use as variáveis com prefixo `K6_` definidas em `docker-compose.yml`:

```bash
K6_VUS=50 K6_DURATION=1m K6_PRODUCT_ID=1 docker compose --profile benchmark run --rm k6 run /scripts/cache_hot.js
```

## Interpretação dos resultados

Compare os cenários usando a tabela abaixo, gerada a partir dos arquivos em `results/`:

| Cenário | Arquivo | Iterações | Latência média | p95 | Requisições por segundo | Falhas |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Sem cache | `results/no_cache.json` | 600 | 11.08 ms | 45.98 ms | 19.71 req/s | 0% |
| Cache frio | `results/cache_cold.json` | 1 | 5.70 ms | 5.70 ms | N/A | 0% |
| Cache quente | `results/cache_hot.json` | 600 | 2.32 ms | 3.97 ms | 19.97 req/s | 0% |
| Carga mista | `results/mixed_load.json` | 600 | 6.14 ms | 33.05 ms | 19.84 req/s | 0% |

O cenário sem cache consulta o PostgreSQL diretamente em todas as leituras. Com cache quente, as leituras são atendidas pelo Redis, reduzindo a latência média de 11.08 ms para 2.32 ms, uma queda de aproximadamente 79%. O p95 caiu de 45.98 ms para 3.97 ms, uma redução de aproximadamente 91%. O cache frio foi executado com apenas 1 iteração para demonstrar o comportamento de `MISS`: a aplicação consulta o banco, popula o Redis e deixa o dado pronto para leituras seguintes. Por ter apenas uma iteração, sua taxa de requisições por segundo não é comparável aos cenários de 30 segundos.

O throughput ficou parecido entre os cenários principais: 19.71 req/s sem cache, 19.97 req/s com cache quente e 19.84 req/s na carga mista. Isso acontece porque os scripts de benchmark usam pausa entre iterações, o que limita a taxa de requisições gerada pelo teste. Por isso, a comparação principal deve ser feita pela latência média e pelo p95, não pela vazão.

A comparação principal deve observar:

- latência média e percentis (`http_req_duration`);
- quantidade de requisições por segundo como métrica secundária;
- diferença entre cache hit e cache miss;
- redução de consultas ao PostgreSQL quando o Redis atende as leituras.

## Status

A aplicação contém a base FastAPI, integração com PostgreSQL e Redis, endpoints de leitura sem cache, leitura com cache-aside, métricas em memória, invalidação de cache em atualização/remoção, criação write-through, testes automatizados e scripts de benchmark k6. O checklist de implementação está concluído em [TODO.md](TODO.md).
