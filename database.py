import sqlite3

DATABASE = 'pharmacy.db'

def connect():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            full_name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول الأدوية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            pharmacy_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول طلبات الأطباء
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctor_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            department TEXT NOT NULL,
            medicine_name TEXT NOT NULL,
            dose TEXT NOT NULL,
            notes TEXT,
            pharmacy_type TEXT,
            status TEXT DEFAULT 'Pending',
            pharmacist_name TEXT,
            dispense_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # جدول الموردين - جديد
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            drug_name TEXT NOT NULL,
            batch_number TEXT NOT NULL,
            supply_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()