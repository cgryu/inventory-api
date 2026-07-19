from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True

class ItemOut(Item):
    price_with_tax: float

class IteminDB(Item):
    secret: str = "internal"

class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    in_stock: bool | None = None

items_db: dict[int, IteminDB] = {}
itemID = 1
taxRate = 0.05

def calculate_tax(item: Item):
    return ItemOut(**item.model_dump(), price_with_tax=item.price*(1+taxRate))

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/items/{item_id}", response_model=ItemOut)
def read_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return calculate_tax(items_db[item_id])

@app.get("/items", response_model=list[ItemOut])
def list_items(limit: int = 10, skip: int = 0):
    return [calculate_tax(item) for item in list(items_db.values())[skip:skip+limit]]
        

@app.post("/items", response_model=ItemOut)
def create_item(item: Item):
    global itemID
    items_db[itemID] = IteminDB(**item.model_dump())
    oldID = itemID
    itemID += 1
    return calculate_tax(items_db[oldID])

@app.put("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, item: Item):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
        
    items_db[item_id] = IteminDB(**item.model_dump())
    return calculate_tax(items_db[item_id])

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    items_db.pop(item_id)
    return {"status": "ok"}

@app.patch("/items/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, update: ItemUpdate):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    patch_data = update.model_dump(exclude_unset=True)
    merged = items_db[item_id].model_dump() | patch_data
    try:
        items_db[item_id] = IteminDB(**merged)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    return calculate_tax(items_db[item_id])