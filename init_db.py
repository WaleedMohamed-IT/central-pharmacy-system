import sqlite3

def init_db():
    conn = sqlite3.connect("pharmacy.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL
    )
    """)

    conn.commit()
    conn.close()

    print("Database initialized successfully ✔")


if __name__ == "__main__":
    init_db()