from flask import Flask, render_template, request, redirect, url_for, session, send_file
import database
from pharmacy_users_management import users_bp, init_users_db
from datetime import datetime, timedelta
import io
import os
import csv
import hashlib

# Try to load dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

# =========================
# CONFIGURATION
# =========================
app.secret_key = os.getenv('SECRET_KEY', 'pharmacy_secret_key_2024_dev')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# =========================
# INIT DATABASE
# =========================
database.init_db()
init_users_db()
app.register_blueprint(users_bp)

# =========================
# PERMISSION CHECKER
# =========================
def check_permission(allowed_roles):
    if 'role' not in session or session.get('role') not in allowed_roles:
        return False
    return True

def require_roles(*roles):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not check_permission(roles):
                return render_template('unauthorized.html'), 403
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# =========================
# CONTEXT PROCESSORS
# =========================
@app.context_processor
def inject_user():
    return {
        'current_user': session.get('user'),
        'current_role': session.get('role')
    }

# =========================
# HOME PAGE
# =========================
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            error = "❌ اسم المستخدم وكلمة المرور مطلوبان"
        else:
            conn = database.connect()
            hashed = hashlib.sha256(password.encode()).hexdigest()
            user = conn.execute(
                "SELECT * FROM users WHERE username=? AND password=? AND is_active=1",
                (username, hashed)
            ).fetchone()
            conn.close()

            if user:
                session['user'] = user['username']
                session['role'] = user['role']
                session.permanent = True
                return redirect(url_for('dashboard'))
            else:
                error = "❌ اسم المستخدم أو كلمة المرور غير صحيحة"

    return render_template("login.html", error=error)

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")

# =========================
# PHARMACIES MENU
# =========================
@app.route('/pharmacies')
def pharmacies():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("pharmacies.html")

# =========================
# MEDICINES LIST
# =========================
@app.route('/medicines')
def medicines():
    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()
    conn = database.connect()

    if search:
        rows = conn.execute(
            "SELECT * FROM medicines WHERE name LIKE ? ORDER BY id DESC",
            ('%' + search + '%',)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM medicines ORDER BY id DESC").fetchall()

    conn.close()
    return render_template("medicines.html", medicines=rows, search=search)

# =========================
# ADD MEDICINE
# =========================
@app.route('/add', methods=['GET', 'POST'])
@require_roles('admin', 'pharmacist')
def add():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            price = request.form.get('price', '').strip()
            quantity = request.form.get('quantity', '').strip()
            pharmacy_type = request.form.get('pharmacy_type', '').strip()

            if not all([name, price, quantity, pharmacy_type]):
                return render_template("add.html", error="جميع الحقول مطلوبة")

            conn = database.connect()
            conn.execute(
                "INSERT INTO medicines (name, price, quantity, pharmacy_type) VALUES (?, ?, ?, ?)",
                (name, float(price), int(quantity), pharmacy_type)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('medicines'))
        except ValueError:
            return render_template("add.html", error="يرجى إدخال أرقام صحيحة")

    return render_template("add.html")

# =========================
# EDIT MEDICINE
# =========================
@app.route('/edit/<int:med_id>', methods=['GET', 'POST'])
@require_roles('admin', 'pharmacist')
def edit(med_id):
    conn = database.connect()

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            price = request.form.get('price', '').strip()
            quantity = request.form.get('quantity', '').strip()

            if not all([name, price, quantity]):
                return render_template("edit.html", error="جميع الحقول مطلوبة")

            conn.execute(
                "UPDATE medicines SET name=?, price=?, quantity=? WHERE id=?",
                (name, float(price), int(quantity), med_id)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('medicines'))
        except ValueError:
            conn.close()
            return render_template("edit.html", error="يرجى إدخال أرقام صحيحة")

    medicine = conn.execute("SELECT * FROM medicines WHERE id=?", (med_id,)).fetchone()
    conn.close()

    if not medicine:
        return redirect(url_for('medicines'))

    return render_template("edit.html", medicine=medicine)

# =========================
# DELETE MEDICINE
# =========================
@app.route('/delete/<int:med_id>')
@require_roles('admin')
def delete(med_id):
    conn = database.connect()
    conn.execute("DELETE FROM medicines WHERE id=?", (med_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('medicines'))

# =========================
# DOCTOR ORDER
# =========================
@app.route('/doctor-order', methods=['GET', 'POST'])
@require_roles('doctor', 'admin')
def doctor_order():
    if request.method == 'POST':
        try:
            patient_name = request.form.get('patient_name', '').strip()
            patient_id = request.form.get('patient_id', '').strip()
            department = request.form.get('department', '').strip()
            medicine_name = request.form.get('medicine_name', '').strip()
            dose = request.form.get('dose', '').strip()
            notes = request.form.get('notes', '').strip()
            pharmacy_type = request.form.get('pharmacy_type', '').strip()

            if not all([patient_name, patient_id, department, medicine_name, dose, pharmacy_type]):
                return render_template("doctor_order.html", error="الحقول المطلوبة ناقصة")

            conn = database.connect()
            conn.execute("""
                INSERT INTO doctor_orders
                (patient_name, patient_id, department, medicine_name, dose, notes, pharmacy_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
            """, (patient_name, patient_id, department, medicine_name, dose, notes, pharmacy_type))
            conn.commit()
            conn.close()
            return redirect(url_for('pharmacy_orders'))
        except Exception as e:
            return render_template("doctor_order.html", error=f"حدث خطأ: {str(e)}")

    return render_template("doctor_order.html")

# =========================
# PHARMACY ORDERS
# =========================
@app.route('/pharmacy-orders')
def pharmacy_orders():
    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()
    conn = database.connect()

    if search:
        orders = conn.execute("""
            SELECT * FROM doctor_orders
            WHERE patient_name LIKE ? OR medicine_name LIKE ?
            ORDER BY id DESC
        """, ('%' + search + '%', '%' + search + '%')).fetchall()
    else:
        orders = conn.execute("SELECT * FROM doctor_orders ORDER BY id DESC").fetchall()

    pending_count = conn.execute(
        "SELECT COUNT(*) FROM doctor_orders WHERE status='Pending'"
    ).fetchone()[0]

    approved_count = conn.execute(
        "SELECT COUNT(*) FROM doctor_orders WHERE status='Approved'"
    ).fetchone()[0]

    rejected_count = conn.execute(
        "SELECT COUNT(*) FROM doctor_orders WHERE status='Rejected'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "pharmacy_orders.html",
        orders=orders,
        search=search,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count
    )

# =========================
# APPROVE ORDER
# =========================
@app.route('/approve/<int:order_id>')
def approve(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = database.connect()
    conn.execute("""
        UPDATE doctor_orders
        SET status='Approved',
            pharmacist_name=?,
            dispense_time=?
        WHERE id=?
    """, (session.get('user'), datetime.now().strftime("%Y-%m-%d %H:%M"), order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('pharmacy_orders'))

# =========================
# REJECT ORDER
# =========================
@app.route('/reject/<int:order_id>')
def reject(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    conn = database.connect()
    conn.execute("""
        UPDATE doctor_orders
        SET status='Rejected',
            pharmacist_name=?,
            dispense_time=?
        WHERE id=?
    """, (session.get('user'), datetime.now().strftime("%Y-%m-%d %H:%M"), order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('pharmacy_orders'))

# =========================
# EXPORT EXCEL
# =========================
@app.route('/export/excel')
@require_roles('admin', 'pharmacist')
def export_excel():
    conn = database.connect()
    orders = conn.execute("SELECT * FROM doctor_orders ORDER BY id DESC").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Patient Name', 'Patient ID', 'Department',
        'Medicine', 'Dose', 'Notes', 'Status',
        'Pharmacist', 'Dispense Time', 'Pharmacy Type', 'Created At'
    ])

    for order in orders:
        writer.writerow(list(order))

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='pharmacy_orders.csv'
    )

# =========================
# EXPORT PDF
# =========================
@app.route('/export/pdf')
@require_roles('admin', 'pharmacist')
def export_pdf():
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    conn = database.connect()
    orders = conn.execute("SELECT * FROM doctor_orders ORDER BY id DESC").fetchall()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []

    styles = getSampleStyleSheet()
    elements.append(Paragraph("تقرير طلبات الصيدلية", styles['Title']))
    elements.append(Paragraph(
        f"تم الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles['Normal']
    ))
    elements.append(Spacer(1, 20))

    data = [[
        'ID', 'المريض', 'رقم المريض', 'القسم',
        'الدواء', 'الجرعة', 'الحالة', 'الصيدلي', 'الوقت'
    ]]

    for order in orders:
        data.append([
            str(order['id']),
            order['patient_name'],
            order['patient_id'],
            order['department'],
            order['medicine_name'],
            order['dose'],
            order['status'],
            order['pharmacist_name'] or '-',
            order['dispense_time'] or '-'
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='pharmacy_orders.pdf'
    )

# =========================
# NOTIFICATIONS
# =========================
@app.route('/check-new-orders')
def check_new_orders():
    if 'user' not in session or session.get('role') != 'pharmacist':
        return {'count': 0}
    
    conn = database.connect()
    pending = conn.execute(
        "SELECT COUNT(*) FROM doctor_orders WHERE status='Pending'"
    ).fetchone()[0]
    conn.close()
    
    return {'count': pending}

# =========================
# SUPPLIERS (الموردين)
# =========================
@app.route('/suppliers')
def suppliers():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    search = request.args.get('search', '').strip()
    conn = database.connect()
    
    if search:
        rows = conn.execute("""
            SELECT * FROM suppliers 
            WHERE company_name LIKE ? OR drug_name LIKE ?
            ORDER BY id DESC
        """, ('%' + search + '%', '%' + search + '%')).fetchall()
    else:
        rows = conn.execute("SELECT * FROM suppliers ORDER BY id DESC").fetchall()
    
    conn.close()
    return render_template("suppliers.html", suppliers=rows, search=search, now=datetime.now(), timedelta=timedelta)

@app.route('/add-supplier', methods=['GET', 'POST'])
@require_roles('admin', 'pharmacist')
def add_supplier():
    if request.method == 'POST':
        try:
            company_name = request.form.get('company_name', '').strip()
            drug_name = request.form.get('drug_name', '').strip()
            batch_number = request.form.get('batch_number', '').strip()
            supply_date = request.form.get('supply_date', '').strip()
            expiry_date = request.form.get('expiry_date', '').strip()
            price = request.form.get('price', '').strip()
            quantity = request.form.get('quantity', '').strip()
            
            if not all([company_name, drug_name, batch_number, supply_date, expiry_date, price, quantity]):
                return render_template("add_supplier.html", error="جميع الحقول مطلوبة")
            
            conn = database.connect()
            conn.execute("""
                INSERT INTO suppliers 
                (company_name, drug_name, batch_number, supply_date, expiry_date, price, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_name, drug_name, batch_number, supply_date, expiry_date, float(price), int(quantity)))
            conn.commit()
            conn.close()
            
            return redirect(url_for('suppliers'))
        except ValueError:
            return render_template("add_supplier.html", error="يرجى إدخال أرقام صحيحة")
    
    return render_template("add_supplier.html")

@app.route('/edit-supplier/<int:supplier_id>', methods=['GET', 'POST'])
@require_roles('admin', 'pharmacist')
def edit_supplier(supplier_id):
    conn = database.connect()
    
    if request.method == 'POST':
        try:
            company_name = request.form.get('company_name', '').strip()
            drug_name = request.form.get('drug_name', '').strip()
            batch_number = request.form.get('batch_number', '').strip()
            supply_date = request.form.get('supply_date', '').strip()
            expiry_date = request.form.get('expiry_date', '').strip()
            price = request.form.get('price', '').strip()
            quantity = request.form.get('quantity', '').strip()
            
            if not all([company_name, drug_name, batch_number, supply_date, expiry_date, price, quantity]):
                return render_template("edit_supplier.html", error="جميع الحقول مطلوبة")
            
            conn.execute("""
                UPDATE suppliers 
                SET company_name=?, drug_name=?, batch_number=?, supply_date=?, expiry_date=?, price=?, quantity=?
                WHERE id=?
            """, (company_name, drug_name, batch_number, supply_date, expiry_date, float(price), int(quantity), supplier_id))
            conn.commit()
            conn.close()
            return redirect(url_for('suppliers'))
        except ValueError:
            conn.close()
            return render_template("edit_supplier.html", error="يرجى إدخال أرقام صحيحة")
    
    supplier = conn.execute("SELECT * FROM suppliers WHERE id=?", (supplier_id,)).fetchone()
    conn.close()
    
    if not supplier:
        return redirect(url_for('suppliers'))
    
    return render_template("edit_supplier.html", supplier=supplier)

@app.route('/delete-supplier/<int:supplier_id>')
@require_roles('admin')
def delete_supplier(supplier_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = database.connect()
    conn.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('suppliers'))

# =========================
# ERROR HANDLERS
# =========================
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.getenv('PORT', 5000))
    
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=port
    )