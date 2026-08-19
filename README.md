# inventory-api

A small but production-shaped REST API: **authenticated CRUD over PostgreSQL, deployed on Railway.** Built to practice the backend stack the way it's actually run in production — raw SQL, real token auth, a real deploy — rather than as a tutorial toy.

## Stack

- **FastAPI** (Python) — routing and request/response validation via Pydantic
- **PostgreSQL**, accessed with **psycopg 3** — raw, parameterized SQL, no ORM
- **Clerk** — identity provider; the API verifies Clerk-issued RS256 JWTs
- **Railway** — hosting and managed Postgres

## What it does

CRUD over an `items` inventory resource, scoped per authenticated user:

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/items` | Create an item (owner = the caller's user id) |
| `GET` | `/items` | List the caller's items (paginated) |
| `GET` | `/items/{id}` | Read one item |
| `PATCH` | `/items/{id}` | Partial update |
| `DELETE` | `/items/{id}` | Delete |
| `GET` | `/me` | Return the authenticated user id (auth smoke-test) |

## Design decisions

The point of the project is the reasoning, not the endpoints.

**Raw SQL over an ORM.** Every query is hand-written and parameterized through psycopg. This keeps the data access transparent (no query-generation magic to reason about) and maps directly onto the raw-SQL style used by tools like `sqlx`, rather than hiding behind an abstraction.

**Connection pooling with one transaction owner per request.** A `psycopg_pool` connection pool (min 1, max 10) is opened at startup inside a FastAPI `lifespan` context. Each request checks out a connection, and the connection's context manager owns the transaction — it commits on a clean exit and rolls back on any raised exception. One owner per request means there is exactly one place a transaction can be committed or leaked, which is what makes the error paths safe on a shared pool.

**Verify the token, don't trust it.** Auth is done by verifying each request's RS256 JWT signature against Clerk's static public key with PyJWT, plus a small `leeway` to absorb clock skew between hosts. `python-jose` is deliberately avoided (algorithm-confusion CVE).

**Ownership enforced at the data layer.** Every row carries a `user_id`. The owner is read from the verified token's `sub` claim — never from the request body, so a client can't declare itself the owner of someone else's data. Every read and write filters by owner. A request for a row you don't own returns **404, not 403**, so the API never confirms the existence of a row it won't show you (no enumeration signal).

**Money as `NUMERIC`, not float.** Prices use `NUMERIC(10,2)` for exact decimal semantics; psycopg returns `Decimal` and Pydantic coerces on output.

**Integrity errors translated at the boundary.** A `UNIQUE` violation is caught and returned as a `409`, not a `500`. A 500 means the server broke; a 4xx means the request was bad — the boundary is where that distinction gets made.

## Run locally

```bash
pip install -r requirements.txt

export DATABASE_URL="postgres://<user>:<pass>@<host>:<port>/<db>"
export CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----"

uvicorn main:app --reload
```

The schema lives in `schema.sql`. On Railway, `DATABASE_URL` is supplied via a `${{Postgres.DATABASE_URL}}` reference variable and the Clerk key is set in the service's environment.

## Known limitations

Called out deliberately rather than hidden:

- **Item-name uniqueness is currently global.** Two different users can't reuse a name. The fix is a composite `UNIQUE (user_id, name)` so uniqueness is scoped per user.
- **No rate limiting.**
- **`/docs` is intentionally public.** It exposes the schema, not data, and every data route enforces auth independently. In a real production service you'd gate or disable it as attack-surface reduction.
- **API only** — there is no frontend by design.
