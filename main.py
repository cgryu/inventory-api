from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True

class IteminDB(Item):
    secret: str = "internal"

items_db: dict[int, IteminDB] = {}
itemID = 1

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.get("/items", response_model=list[Item])
def list_items(limit: int = 10, skip: int = 0):
    return list(items_db.values())[skip:skip+limit]

@app.post("/items")
def create_item(item: Item):
    global itemID
    item.price *= 1.05
    items_db[itemID] = IteminDB(**item.model_dump())
    itemID += 1
    return {"received": item, "price_with_tax": item.price}

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: Item):
    if item_id in items_db:
        items_db[item_id] = IteminDB(**item.model_dump())
    else:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id in items_db:
        items_db.pop(item_id)
    else:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "ok"}