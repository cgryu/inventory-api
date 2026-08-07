CREATE TABLE items (
    item_id  SERIAL PRIMARY KEY,
    name     TEXT NOT NULL UNIQUE,
    price    NUMERIC(10, 2) NOT NULL,
    in_stock BOOLEAN NOT NULL DEFAULT TRUE
);