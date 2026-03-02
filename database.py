import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="grocery_db",
        user="postgres",
        password="postgres123",
        port=5432
    )
    return conn
