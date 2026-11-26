CREATE TABLE customers (
    id integer PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE orders (
    id integer PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(id),
    amount_eur numeric(10, 2) NOT NULL
);

INSERT INTO customers (id, name)
VALUES (1, 'Alice'), (2, 'Karim');

INSERT INTO orders (id, customer_id, amount_eur)
VALUES (1, 1, 120), (2, 1, 80), (3, 2, 150);

CREATE ROLE schema_pilot_reader LOGIN PASSWORD 'demo_reader';
GRANT USAGE ON SCHEMA public TO schema_pilot_reader;
GRANT SELECT ON customers, orders TO schema_pilot_reader;