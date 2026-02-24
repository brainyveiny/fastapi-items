from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import json
import os

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    description: str | None = None

DB_FILE = "items.json"

def load_items():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        data = json.load(f)
    return {int(k): Item(**v) for k, v in data.items()}

def save_items(items: Dict[int, Item]):
    with open(DB_FILE, "w") as f:
        json.dump({k: v.dict() for k, v in items.items()}, f)

@app.get("/items/{item_id}")
def read_item(item_id: int):
    items = load_items()
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]

@app.post("/items/{item_id}")
def create_item(item_id: int, item: Item):
    items = load_items()
    if item_id in items:
        raise HTTPException(status_code=400, detail="Item already exists")
    items[item_id] = item
    save_items(items)
    return {"message": "Item created", "item": item}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    items = load_items()
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    items[item_id] = item
    save_items(items)
    return {"message": "Item updated", "item": item}

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    items = load_items()
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    del items[item_id]
    save_items(items)
    return {"message": "Item deleted"}