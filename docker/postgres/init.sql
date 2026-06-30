CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(12, 2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO products (name, description, price, stock)
VALUES
    ('Notebook Acadêmico', 'Produto inicial para testes sem cache e com cache.', 4299.90, 10),
    ('Monitor 27 Pol', 'Carga inicial para benchmark k6.', 1499.00, 15),
    ('Teclado Mecânico', 'Item usado em cenários de leitura repetida.', 399.90, 30)
ON CONFLICT DO NOTHING;

