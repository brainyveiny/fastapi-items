import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from jose import JWTError

from database import get_connection
from auth import hash_password, verify_password, create_access_token, decode_access_token

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    description: str | None = None

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str | None = None

class UserRegister(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")

@app.on_event("startup")
def create_tables():
    logger.info("App is starting")
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Tables created")

@app.post("/auth/register", tags=["Auth"])
def register(user: UserRegister, conn=Depends(get_db)):
    logger.info(f"Registering user: {user.username}")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (user.username,))
    if cur.fetchone():
        logger.warning(f"Username already taken: {user.username}")
        cur.close()
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed = hash_password(user.password)
    cur.execute("INSERT INTO users (username, hashed_password) VALUES (%s, %s)", (user.username, hashed))
    conn.commit()
    cur.close()
    logger.info(f"User registered: {user.username}")
    return {"message": "User registered successfully"}

@app.post("/auth/login", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), conn=Depends(get_db)):
    logger.info(f"Login attempt: {form_data.username}")
    cur = conn.cursor()
    cur.execute("SELECT id, hashed_password FROM users WHERE username = %s", (form_data.username,))
    row = cur.fetchone()
    cur.close()
    if not row or not verify_password(form_data.password, row[1]):
        logger.warning(f"Login failed: {form_data.username}")
        raise HTTPException(status_code=401, detail="Wrong username or password")
    token = create_access_token({"sub": form_data.username})
    logger.info(f"Login successful: {form_data.username}")
    return {"access_token": token, "token_type": "bearer"}

@app.post("/items/{item_id}", tags=["CRUD"])
def create_item(item_id: int, item: Item, conn=Depends(get_db), current_user: str = Depends(get_current_user)):
    logger.info(f"Creating item {item_id} by {current_user}")
    cur = conn.cursor()
    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if cur.fetchone():
        logger.warning(f"Item {item_id} already exists")
        cur.close()
        raise HTTPException(status_code=400, detail="Item already exists")
    cur.execute("INSERT INTO items (id, name, price, description) VALUES (%s, %s, %s, %s)", (item_id, item.name, item.price, item.description))
    conn.commit()
    cur.close()
    logger.info(f"Item {item_id} created")
    return {"id": item_id, "name": item.name, "price": item.price, "description": item.description}

@app.get("/items/{item_id}", tags=["CRUD"])
def read_item(item_id: int, conn=Depends(get_db), current_user: str = Depends(get_current_user)):
    logger.debug(f"Reading item {item_id}")
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, description FROM items WHERE id = %s", (item_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        logger.warning(f"Item {item_id} not found")
        raise HTTPException(status_code=404, detail="Item not found")
    logger.info(f"Item {item_id} found")
    return {"id": row[0], "name": row[1], "price": row[2], "description": row[3]}

@app.put("/items/{item_id}", tags=["CRUD"])
def update_item(item_id: int, item: Item, conn=Depends(get_db), current_user: str = Depends(get_current_user)):
    logger.info(f"Updating item {item_id} by {current_user}")
    cur = conn.cursor()
    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if not cur.fetchone():
        logger.warning(f"Item {item_id} not found for update")
        cur.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cur.execute("UPDATE items SET name = %s, price = %s, description = %s WHERE id = %s", (item.name, item.price, item.description, item_id))
    conn.commit()
    cur.close()
    logger.info(f"Item {item_id} updated")
    return {"id": item_id, "name": item.name, "price": item.price, "description": item.description}

@app.delete("/items/{item_id}", tags=["CRUD"])
def delete_item(item_id: int, conn=Depends(get_db), current_user: str = Depends(get_current_user)):
    logger.info(f"Deleting item {item_id} by {current_user}")
    cur = conn.cursor()
    cur.execute("SELECT id FROM items WHERE id = %s", (item_id,))
    if not cur.fetchone():
        logger.warning(f"Item {item_id} not found for delete")
        cur.close()
        raise HTTPException(status_code=404, detail="Item not found")
    cur.execute("DELETE FROM items WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    logger.info(f"Item {item_id} deleted")
    return {"message": "Item deleted"}
