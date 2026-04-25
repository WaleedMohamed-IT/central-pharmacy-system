import sqlite3
import pandas as pd
import hashlib
import os

# قراءة ملف الأدوية
print("📖 جاري قراءة ملف الأدوية...")
df_drugs = pd.read_excel('Drugs.xlsx')

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('pharmacy.db')
cursor = conn.cursor()

# ============ استيراد الأدوية ============
print(f"\n💊 جاري استيراد {len(df_drugs)} دواء...")

count = 0
for index, row in df_drugs.iterrows():
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO medicines 
            (name, price, quantity, pharmacy_type) 
            VALUES (?, ?, ?, ?)
        """, (
            row['DrugName'],
            0,
            int(row['Stock']),
            row['Unit']
        ))
        count += 1
    except Exception as e:
        print(f"❌ خطأ في الدواء {index}: {e}")

conn.commit()
print(f"✅ تم استيراد {count} دواء بنجاح!")

# ============ استيراد المستخدمين ============
print("\n👥 جاري استيراد المستخدمين الجدد...")

users = [
    {
        'name': 'وليد محمد محمد',
        'username': 'waleed',
        'password': '123456',
        'role': 'doctor'
    },
    {
        'name': 'اسر وليد محمد',
        'username': 'asser',
        'password': '123456',
        'role': 'pharmacist'
    }
]

for user in users:
    try:
        hashed_password = hashlib.sha256(user['password'].encode()).hexdigest()
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (username, password, role, is_active, full_name) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            user['username'],
            hashed_password,
            user['role'],
            1,
            user['name']
        ))
        print(f"✅ تم إضافة المستخدم: {user['username']} ({user['role']})")
    except Exception as e:
        print(f"❌ خطأ في المستخدم {user['username']}: {e}")

conn.commit()
conn.close()

print("\n" + "="*50)
print("🎉 انتهى الاستيراد بنجاح!")
print("="*50)
print(f"\n📊 ملخص:")
print(f"  ✅ {count} دواء")
print(f"  ✅ {len(users)} مستخدم جديد")
print(f"\n🔑 بيانات الدخول:")
for user in users:
    print(f"  • {user['username']} / {user['password']} ({user['role']})")