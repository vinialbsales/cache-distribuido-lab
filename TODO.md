# Plano de Implementação

## 1. Base da aplicação

- [x] Criar estrutura de pastas do projeto.
- [x] Criar `docker-compose.yml` com API, PostgreSQL e Redis.
- [x] Criar `Dockerfile` e `requirements.txt`.
- [x] Criar README inicial.
- [x] Criar plano de implementação.
- [x] Configurar carregamento de variáveis de ambiente.
- [x] Configurar conexão assíncrona com PostgreSQL.
- [x] Configurar cliente Redis.

## 2. Modelo de domínio

- [x] Criar modelo `Product`.
- [x] Criar schemas Pydantic para leitura, criação e atualização de produtos.
- [x] Criar camada de serviço para acesso ao PostgreSQL.
- [x] Definir padrão de chave Redis: `product:{id}`.

## 3. Endpoint sem cache

- [x] Implementar `GET /products/{id}/no-cache` consultando diretamente o PostgreSQL.
- [x] Adicionar tratamento para produto não encontrado.
- [x] Criar testes automatizados do endpoint.

## 4. Cache-aside

- [x] Implementar serviço de cache para serializar e desserializar produtos.
- [x] Implementar `GET /products/{id}/cache`.
- [x] Registrar cache hit e cache miss.
- [x] Gravar produto no Redis com TTL configurável após cache miss.
- [x] Criar testes para cache hit e cache miss.

## 5. Invalidação

- [x] Implementar `PUT /products/{id}`.
- [x] Atualizar produto no PostgreSQL.
- [x] Invalidar ou atualizar a chave Redis correspondente.
- [x] Implementar `DELETE /products/{id}` invalidando a chave Redis.
- [x] Criar testes para garantir que dados antigos não continuam no cache.
- [x] Criar testes para garantir que produto removido deixa de ser retornado.

## 6. Write-through

- [x] Implementar `POST /products/write-through`.
- [x] Gravar produto no PostgreSQL.
- [x] Gravar produto no Redis no mesmo fluxo.
- [x] Criar testes para validar persistência no banco e no cache.

## 7. Métricas de cache

- [x] Implementar contadores de hits e misses.
- [x] Implementar `GET /metrics/cache`.
- [x] Retornar hits, misses, total de leituras cacheadas e taxa de acerto.
- [x] Criar testes das métricas.

## 8. Benchmark com k6

- [x] Ajustar scripts k6 para cenários separados: sem cache, cache miss e cache hit.
- [x] Criar cenário k6 de carga mista com leituras cacheadas, leituras sem cache e atualizações.
- [x] Documentar comandos de benchmark no README.
- [x] Incluir tabela de resultados no README.
- [x] Incluir orientação de interpretação dos resultados.
- [x] Adicionar serviço k6 opcional no Docker Compose.

## 9. Qualidade e documentação final

- [x] Revisar README com arquitetura completa.
- [x] Adicionar exemplos de requisições `curl`.
- [x] Garantir que `pytest` execute no container.
- [x] Validar `docker compose up --build`.
- [x] Revisar organização final do projeto.
