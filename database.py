"""
database.py - إدارة قاعدة البيانات للصيدلية
"""

import sqlite3
from datetime import datetime
import hashlib
import os

DATABASE = 'pharmacy.db'

def init_db():
    """إنشاء قاعدة البيانات والجداول"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول الأدوية
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scientific_name TEXT,
            quantity INTEGER DEFAULT 0,
            pharmacy_type TEXT,
            min_quantity INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # جدول طلبات الأطباء
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            department TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines(id),
            FOREIGN KEY (doctor_id) REFERENCES users(id)
        )
    ''')

    # جدول طلبات الصيدلية (الموافقة/الرفض)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pharmacy_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_order_id INTEGER NOT NULL,
            pharmacist_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_order_id) REFERENCES doctor_orders(id),
            FOREIGN KEY (pharmacist_id) REFERENCES users(id)
        )
    ''')

    # جدول تفاصيل الصرف (جديد)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescription_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pharmacy_order_id INTEGER NOT NULL,
            pharmacist_id INTEGER NOT NULL,
            nurse_name TEXT NOT NULL,
            medicine_id INTEGER NOT NULL,
            quantity_dispensed INTEGER NOT NULL,
            dispensed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (pharmacy_order_id) REFERENCES pharmacy_orders(id),
            FOREIGN KEY (pharmacist_id) REFERENCES users(id),
            FOREIGN KEY (medicine_id) REFERENCES medicines(id)
        )
    ''')

    # جدول سجل الأنشطة (جديد)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            description TEXT,
            target_type TEXT,
            target_id INTEGER,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

def add_default_admin():
    """إضافة مستخدم admin افتراضي"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        hashed_password = hashlib.sha256('admin1234'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (username, password, role, is_active)
            VALUES (?, ?, ?, ?)
        ''', ('admin', hashed_password, 'admin', 1))
        conn.commit()
        print("✓ تم إضافة مستخدم admin افتراضي")
    except sqlite3.IntegrityError:
        print("✓ مستخدم admin موجود بالفعل")
    finally:
        conn.close()

def get_connection():
    """الحصول على اتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== MEDICINES ====================

def add_medicine(name, scientific_name, quantity, pharmacy_type, min_quantity=10):
    """إضافة دواء جديد"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO medicines (name, scientific_name, quantity, pharmacy_type, min_quantity)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, scientific_name, quantity, pharmacy_type, min_quantity))
    conn.commit()
    conn.close()
    return cursor.lastrowid

def get_medicines():
    """الحصول على جميع الأدوية"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM medicines ORDER BY name')
    medicines = cursor.fetchall()
    conn.close()
    return medicines

def get_medicine(medicine_id):
    """الحصول على دواء واحد"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM medicines WHERE id = ?', (medicine_id,))
    medicine = cursor.fetchone()
    conn.close()
    return medicine

def update_medicine(medicine_id, name, scientific_name, quantity, pharmacy_type, min_quantity):
    """تحديث بيانات دواء"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE medicines 
        SET name = ?, scientific_name = ?, quantity = ?, pharmacy_type = ?, min_quantity = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (name, scientific_name, quantity, pharmacy_type, min_quantity, medicine_id))
    conn.commit()
    conn.close()

def delete_medicine(medicine_id):
    """حذف دواء"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM medicines WHERE id = ?', (medicine_id,))
    conn.commit()
    conn.close()

def search_medicines(search_term):
    """البحث عن أدوية"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM medicines 
        WHERE name LIKE ? OR scientific_name LIKE ?
        ORDER BY name
    ''', (f'%{search_term}%', f'%{search_term}%'))
    medicines = cursor.fetchall()
    conn.close()
    return medicines

# ==================== USERS ====================

def add_user(username, password, role):
    """إضافة مستخدم جديد"""
    conn = get_connection()
    cursor = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor.execute('''
            INSERT INTO users (username, password, role, is_active)
            VALUES (?, ?, ?, 1)
        ''', (username, hashed_password, role))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_user(username):
    """الحصول على مستخدم من اسم المستخدم"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    """الحصول على مستخدم من ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_password(username, password):
    """التحقق من كلمة المرور"""
    user = get_user(username)
    if user:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return user['password'] == hashed_password
    return False

def get_all_users():
    """الحصول على جميع المستخدمين"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, is_active FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def update_user(user_id, username, role, is_active):
    """تحديث بيانات مستخدم"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET username = ?, role = ?, is_active = ?
        WHERE id = ?
    ''', (username, role, is_active, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """حذف مستخدم"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

# ==================== DOCTOR ORDERS ====================

def add_doctor_order(medicine_id, doctor_id, quantity, department):
    """إضافة طلب من طبيب"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO doctor_orders (medicine_id, doctor_id, quantity, department, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (medicine_id, doctor_id, quantity, department))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

def get_doctor_orders():
    """الحصول على جميع طلبات الأطباء"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT do.*, m.name as medicine_name, u.username as doctor_name
        FROM doctor_orders do
        JOIN medicines m ON do.medicine_id = m.id
        JOIN users u ON do.doctor_id = u.id
        ORDER BY do.created_at DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_doctor_order(order_id):
    """الحصول على طلب واحد"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT do.*, m.name as medicine_name, u.username as doctor_name
        FROM doctor_orders do
        JOIN medicines m ON do.medicine_id = m.id
        JOIN users u ON do.doctor_id = u.id
        WHERE do.id = ?
    ''', (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

# ==================== PHARMACY ORDERS ====================

def add_pharmacy_order(doctor_order_id, pharmacist_id, status='pending', notes=''):
    """إضافة طلب صيدلية"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pharmacy_orders (doctor_order_id, pharmacist_id, status, notes)
        VALUES (?, ?, ?, ?)
    ''', (doctor_order_id, pharmacist_id, status, notes))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

def get_pharmacy_orders():
    """الحصول على جميع طلبات الصيدلية"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT po.*, do.medicine_id, m.name as medicine_name, u.username as pharmacist_name
        FROM pharmacy_orders po
        JOIN doctor_orders do ON po.doctor_order_id = do.id
        JOIN medicines m ON do.medicine_id = m.id
        JOIN users u ON po.pharmacist_id = u.id
        ORDER BY po.created_at DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

def update_pharmacy_order_status(order_id, status, notes=''):
    """تحديث حالة طلب الصيدلية"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE pharmacy_orders 
        SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, notes, order_id))
    conn.commit()
    conn.close()

# ==================== PRESCRIPTION DETAILS (جديد) ====================

def add_prescription_detail(pharmacy_order_id, pharmacist_id, nurse_name, medicine_id, quantity_dispensed, notes=''):
    """إضافة تفاصيل الصرف"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO prescription_details 
        (pharmacy_order_id, pharmacist_id, nurse_name, medicine_id, quantity_dispensed, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (pharmacy_order_id, pharmacist_id, nurse_name, medicine_id, quantity_dispensed, notes))
    conn.commit()
    detail_id = cursor.lastrowid
    conn.close()
    return detail_id

def get_prescription_details(pharmacy_order_id):
    """الحصول على تفاصيل الصرف لطلب معين"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT pd.*, m.name as medicine_name, u.username as pharmacist_name
        FROM prescription_details pd
        JOIN medicines m ON pd.medicine_id = m.id
        JOIN users u ON pd.pharmacist_id = u.id
        WHERE pd.pharmacy_order_id = ?
        ORDER BY pd.dispensed_at DESC
    ''', (pharmacy_order_id,))
    details = cursor.fetchall()
    conn.close()
    return details

# ==================== ACTIVITY LOG (جديد) ====================

def log_activity(user_id, action, description='', target_type='', target_id=None, ip_address=''):
    """تسجيل نشاط المستخدم"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_log 
        (user_id, action, description, target_type, target_id, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, action, description, target_type, target_id, ip_address))
    conn.commit()
    conn.close()

def get_activity_log(user_id=None, limit=100):
    """الحصول على سجل الأنشطة"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute('''
            SELECT al.*, u.username
            FROM activity_log al
            JOIN users u ON al.user_id = u.id
            WHERE al.user_id = ?
            ORDER BY al.created_at DESC
            LIMIT ?
        ''', (user_id, limit))
    else:
        cursor.execute('''
            SELECT al.*, u.username
            FROM activity_log al
            JOIN users u ON al.user_id = u.id
            ORDER BY al.created_at DESC
            LIMIT ?
        ''', (limit,))
    
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_activity_log_by_date_range(start_date, end_date, user_id=None):
    """الحصول على سجل الأنشطة حسب نطاق زمني"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute('''
            SELECT al.*, u.username
            FROM activity_log al
            JOIN users u ON al.user_id = u.id
            WHERE al.user_id = ? AND DATE(al.created_at) BETWEEN ? AND ?
            ORDER BY al.created_at DESC
        ''', (user_id, start_date, end_date))
    else:
        cursor.execute('''
            SELECT al.*, u.username
            FROM activity_log al
            JOIN users u ON al.user_id = u.id
            WHERE DATE(al.created_at) BETWEEN ? AND ?
            ORDER BY al.created_at DESC
        ''', (start_date, end_date))
    
    logs = cursor.fetchall()
    conn.close()
    return logs

# ==================== STATISTICS ====================

def get_statistics():
    """الحصول على إحصائيات عامة"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # عدد الأدوية
    cursor.execute('SELECT COUNT(*) as count FROM medicines')
    total_medicines = cursor.fetchone()['count']
    
    # عدد الطلبات المعلقة
    cursor.execute("SELECT COUNT(*) as count FROM pharmacy_orders WHERE status = 'pending'")
    pending_orders = cursor.fetchone()['count']
    
    # عدد الطلبات الموافق عليها
    cursor.execute("SELECT COUNT(*) as count FROM pharmacy_orders WHERE status = 'approved'")
    approved_orders = cursor.fetchone()['count']
    
    # عدد الطلبات المرفوضة
    cursor.execute("SELECT COUNT(*) as count FROM pharmacy_orders WHERE status = 'rejected'")
    rejected_orders = cursor.fetchone()['count']
    
    # عدد المستخدمين
    cursor.execute('SELECT COUNT(*) as count FROM users')
    total_users = cursor.fetchone()['count']
    
    conn.close()
    
    return {
        'total_medicines': total_medicines,
        'pending_orders': pending_orders,
        'approved_orders': approved_orders,
        'rejected_orders': rejected_orders,
        'total_users': total_users
    }

if __name__ == '__main__':
    init_db()
    add_default_admin()
    print("✓ تم تهيئة قاعدة البيانات بنجاح!")