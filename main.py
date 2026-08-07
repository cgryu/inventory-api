from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from auth import get_current_user_id
from contextlib import asynccontextmanager
import psycopg
from psycopg_pool import ConnectionPool
import os

pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = ConnectionPool(conninfo=os.environ["DATABASE_URL"], min_size=1, max_size=10, open=True)
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)

def get_conn():
    with pool.connection() as conn:
        yield conn

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

@app.get("/me")
def read_me(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}

@app.get("/items/{item_id}", response_model=ItemOut)
def read_item(item_id: int, conn = Depends(get_conn), user_id: str = Depends(get_current_user_id)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item_id, name, price, in_stock FROM items WHERE item_id = %s AND user_id = %s", 
            (item_id, user_id)
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    saved = Item(name=row[1], price=row[2], in_stock=row[3])
    return to_output(row[0], saved)    

@app.get("/items", response_model=list[ItemOut])
def list_items(limit: int = 10, skip: int = 0, conn = Depends(get_conn), user_id: str = Depends(get_current_user_id)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item_id, name, price, in_stock FROM items WHERE user_id=%s ORDER BY item_id LIMIT %s OFFSET %s", (user_id, limit, skip)
        )
        rows = cur.fetchall()
    return [to_output(item_id, Item(name=name, price=price, in_stock=in_stock)) for (item_id, name, price, in_stock) in rows]

@app.post("/items", response_model=ItemOut, status_code=201)
def create_item(item: Item, conn = Depends(get_conn), user_id: str = Depends(get_current_user_id)):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (name, price, in_stock, user_id) VALUES (%s, %s, %s, %s) RETURNING item_id, name, price, in_stock, user_id",
                (item.name, item.price, item.in_stock, user_id)
            )
            row = cur.fetchone()

    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="item already exists")
    
    saved = Item(name=row[1], price=row[2], in_stock=row[3])
    return to_output(row[0], saved)

@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, conn = Depends(get_conn), user_id: str = Depends(get_current_user_id)):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM items WHERE item_id = %s AND user_id = %s RETURNING item_id", 
            (item_id, user_id)
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    

@app.patch("/items/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, update: ItemUpdate, conn = Depends(get_conn), user_id: str = Depends(get_current_user_id)):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT item_id, name, price, in_stock FROM items WHERE item_id=%s AND user_id=%s",
            (item_id, user_id)
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    old_data = Item(name=row[1], price=row[2], in_stock=row[3]).model_dump()
    patch_data = update.model_dump(exclude_unset=True)
    update_data = old_data | patch_data

    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE items SET name=%s, price=%s, in_stock=%s "
                "WHERE item_id = %s AND user_id = %s "
                "RETURNING item_id, name, price, in_stock",
                (update_data["name"], update_data["price"], update_data["in_stock"], item_id, user_id)
            )
            row = cur.fetchone()

    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Name already exists")

    item_id, name, price, in_stock = row
    return to_output(item_id, Item(name=name, price=price, in_stock=in_stock))