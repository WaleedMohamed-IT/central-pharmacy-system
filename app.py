from flask import Flask, request, redirect, session
from database import get_connection
import matplotlib.pyplot as plt
import io, base64
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook
import os

app = Flask(__name__)
app.secret_key = "pharmacy_secret_key"

# =========================
# 🔐 LOGIN CHECK
# =========================
def login_required():
    return 'user' in session

# =========================
# 🔐 LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin":
            session['user'] = username
            return redirect('/')
        else:
            error = "Invalid login"

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;padding-top:100px;">
        <h2>Login</h2>

        <form method="POST">
            <input name="username" placeholder="Username"><br><br>
            <input name="password" type="password" placeholder="Password"><br><br>
            <button>Login</button>
        </form>

        <p style="color:red;">{error}</p>
        <p>admin / admin</p>
    </body>
    </html>
    """

# =========================
# 🚪 LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# =========================
# 📊 CHART
# =========================
def generate_chart():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, stock FROM medicines WHERE stock < 20")
    data = cursor.fetchall()
    conn.close()

    names = [r["name"] for r in data]
    stocks = [r["stock"] for r in data]

    if not names:
        names = ["No Data"]
        stocks = [0]

    plt.figure(figsize=(6,3))
    plt.bar(names, stocks)
    plt.title("Low Stock Medicines")

    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)

    return base64.b64encode(img.getvalue()).decode()

# =========================
# 🏠 DASHBOARD
# =========================
@app.route('/')
def dashboard():
    if not login_required():
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM medicines")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicines WHERE stock < 20")
    low = cursor.fetchone()[0]

    conn.close()

    chart = generate_chart()

    return f"""
    <html>
    <body style="font-family:Arial;background:#f4f6f9;padding:20px;">

        <h1>📊 Pharmacy System</h1>

        <p>Welcome {session['user']} | <a href="/logout">Logout</a></p>

        <h3>Total Medicines: {total}</h3>
        <h3>Low Stock: {low}</h3>

        <img src="data:image/png;base64,{chart}" width="600">

        <br><br>

        <a href="/medicines_page">Medicines</a> |
        <a href="/export_pdf">PDF</a> |
        <a href="/export_excel">Excel</a>

    </body>
    </html>
    """

# =========================
# 💊 MEDICINES
# =========================
@app.route('/medicines_page')
def medicines_page():
    if not login_required():
        return redirect('/login')

    search = request.args.get("search", "")

    conn = get_connection()
    cursor = conn.cursor()

    if search:
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ?", ('%'+search+'%',))
    else:
        cursor.execute("SELECT * FROM medicines")

    data = cursor.fetchall()
    conn.close()

    rows = ""
    for m in data:
        rows += f"""
        <tr>
            <td>{m['id']}</td>
            <td>{m['name']}</td>
            <td>{m['category']}</td>
            <td>{m['stock']}</td>
            <td>{m['expiry_date']}</td>
            <td>{m['price']}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="font-family:Arial;padding:20px;">

        <h2>Medicines</h2>

        <a href="/">Dashboard</a> |
        <a href="/logout">Logout</a>

        <form>
            <input name="search" placeholder="Search">
            <button>Search</button>
        </form>

        <table border="1" cellpadding="10">
            <tr>
                <th>ID</th><th>Name</th><th>Category</th>
                <th>Stock</th><th>Expiry</th><th>Price</th>
            </tr>
            {rows}
        </table>

    </body>
    </html>
    """

# =========================
# 📄 PDF EXPORT
# =========================
@app.route('/export_pdf')
def export_pdf():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM medicines")
    data = cursor.fetchall()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Pharmacy Report", styles['Title']))
    elements.append(Spacer(1, 12))

    for m in data:
        text = f"{m['id']} - {m['name']} - {m['stock']} - {m['price']}"
        elements.append(Paragraph(text, styles['Normal']))
        elements.append(Spacer(1, 5))

    doc.build(elements)
    buffer.seek(0)

    return buffer.getvalue()

# =========================
# 📊 EXCEL EXPORT
# =========================
@app.route('/export_excel')
def export_excel():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM medicines")
    data = cursor.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active

    ws.append(["ID","Name","Category","Stock","Expiry","Price"])

    for m in data:
        ws.append([m["id"], m["name"], m["category"], m["stock"], m["expiry_date"], m["price"]])

    file = "report.xlsx"
    wb.save(file)

    return redirect(file)

# =========================
# 🚀 RUN (IMPORTANT FOR RENDER)
# =========================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)