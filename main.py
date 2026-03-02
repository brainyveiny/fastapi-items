from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_connection

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    description: str | None = None


@app.on_event("startup")
def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            price FLOAT,
            description VARCHAR(255)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.post("/items/{item_id}")
def create_item(item_id: int, item: Item):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Item already exists")

    cur.execute(
        "INSERT INTO items (id, name, price, description) VALUES (%s, %s, %s, %s)",
        (item_id, item.name, item.price, item.description)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"id": item_id, "name": item.name, "price": item.price, "description": item.description}


@app.get("/items/{item_id}")
def read_item(item_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, price, description FROM items WHERE id = %s", (item_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"id": row[0], "name": row[1], "price": row[2], "description": row[3]}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    cur.execute(
        "UPDATE items SET name = %s, price = %s, description = %s WHERE id = %s",
        (item.name, item.price, item.description, item_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"id": item_id, "name": item.name, "price": item.price, "description": item.description}


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Item not found")

    cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Item deleted"}
