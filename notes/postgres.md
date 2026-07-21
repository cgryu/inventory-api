# Postgres — Slice 1 (Jul 20)

## The four verbs

SELECT — reads rows from a TABLE. `SELECT * FROM items` returns every row;
adding WHERE filters to the rows that match. `*` means all columns, but real
code names the columns it actually needs.

INSERT — adds a row. I must supply any column that's NOT NULL and has no
DEFAULT. I can skip item_id (Postgres generates it), in_stock (defaults TRUE),
and secret (nullable).

UPDATE — edits existing rows. Write the WHERE first. Without one it rewrites
every row in the table and gives no warning.

DELETE — removes existing rows. Same WHERE warning. It prints DELETE 1 vs
DELETE 0, which tells me whether anything was actually there — that's how the
DELETE route picks between 204 and 404.

## Empty results: 404 vs 200

`(0 rows)` means the query succeeded and matched nothing. It's not an error.
The driver translates that: fetchone() gives None, fetchall() gives []. Same
empty result set, different Python value depending on which I call.

The status code depends on WHAT WAS ASKED FOR, not on the emptiness:
- Asked for one resource by id, it isn't there → 404. The thing I named
  doesn't exist.
- Asked for a collection, nothing matched → 200 with