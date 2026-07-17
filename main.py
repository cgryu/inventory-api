from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id, "kind": "widget"}

@app.get("/items")
def list_items(limit: int = 10, skip: int = 0):
    return {"limit": limit, "skip": skip}

@app.post("/items")
def create_item(item: Item):
    return {"received": item, "price_with_tax": item.price * 1.05}