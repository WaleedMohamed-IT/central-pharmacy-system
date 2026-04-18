import sqlite3

def get_connection():
    conn = sqlite3.connect('pharmacy.db')
    conn.row_factory = sqlite3.Row  # عشان يرجّع البيانات بشكل مرتب
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # جدول الأدوية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            stock INTEGER,
            expiry_date TEXT,
            price REAL
        )
    ''')

    # جدول تنبيهات المخزون (للمرحلة الذكية القادمة)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER,
            alert_type TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("Database upgraded successfully 🚀")