from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg
import os

app = FastAPI()
conn = psycopg.connect(
    dbname="playground",
    user="cgryu",
    password=os.environ["DB_PASSWORD"],
    host="localhost"
)

class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True

class ItemOut(Item):
    item_id: int
    price_with_tax: float

class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    in_stock: bool | None = None

taxRate = 0.05

def to_output(item_id: int, item: Item):
    return ItemOut(item_id=item_id, **item.model_dump(), price_with_tax=item.price*(1+taxRate))

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/items/{item_id}", response_model=ItemOut)
def read_item(item_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item_id, name, price, in_stock FROM items WHERE item_id = %s", 
            (item_id,)
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    saved = Item(name=row[1], price=row[2], in_stock=row[3])
    return to_output(row[0], saved)    

@app.get("/items", response_model=list[ItemOut])
def list_items(limit: int = 10, skip: int = 0):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item_id, name, price, in_stock FROM items ORDER BY item_id LIMIT %s OFFSET %s", (limit, skip)
        )
        rows = cur.fetchall()
    return [to_output(item_id, Item(name=name, price=price, in_stock=in_stock)) for (item_id, name, price, in_stock) in rows]

@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: Item):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (name, price, in_stock) VALUES (%s, %s, %s) RETURNING item_id, name, price, in_stock",
                (item.name, item.price, item.in_stock)
            )
            row = cur.fetchone()
            conn.commit()

    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="item already exists")
    
    saved = Item(name=row[1], price=row[2], in_stock=row[3])
    return to_output(row[0], saved)

@app.put("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, item: Item):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE items SET name = %s, price = %s, in_stock =%s "
                "WHERE item_id = %s "
                "RETURNING item_id, name, price, in_stock",
                (item.name, item.price, item.in_stock, item_id)
            )
            row = cur.fetchone()
        if row is None:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Item not found")
        conn.commit()
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Name already exists")
    item_id, name, price, in_stock = row
    return to_output(item_id, Item(name=name, price=price, in_stock=in_stock))

@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM items WHERE item_id = %s RETURNING item_id", 
            (item_id,)
        )
        row = cur.fetchone()

    if row is not None:
        conn.commit()
    else:
        conn.rollback()
        raise HTTPException(status_code=404, detail="Item not found")
    

@app.patch("/items/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, update: ItemUpdate):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item_id, name, price, in_stock FROM items WHERE item_id=%s",
            (item_id,)
        )
        row = cur.fetchone()

    if row is None:
        conn.rollback()
        raise HTTPException(status_code=404, detail="Item not found")

    old_data = Item(name=row[1], price=row[2], in_stock=row[3]).model_dump()
    patch_data = update.model_dump(exclude_unset=True)
    update_data = old_data | patch_data

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE items SET name=%s, price=%s, in_stock=%s "
                "WHERE item_id = %s "
                "RETURNING item_id, name, price, in_stock",
                (update_data["name"], update_data["price"], update_data["in_stock"], item_id)
            )
            row = cur.fetchone()
        conn.commit()

    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Name already exists")

    item_id, name, price, in_stock = row
    return to_output(item_id, Item(name=name, price=price, in_stock=in_stock))