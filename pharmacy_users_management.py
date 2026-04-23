import sqlite3
import hashlib
from functools import wraps
from flask import Blueprint, render_template_string, request, redirect, url_for, session, flash

DB_PATH = "pharmacy.db"

users_bp = Blueprint("users", __name__, url_prefix="/users")


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_users_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            username    TEXT     NOT NULL UNIQUE,
            password    TEXT     NOT NULL,
            full_name   TEXT     NOT NULL DEFAULT '',
            role        TEXT     NOT NULL DEFAULT 'pharmacist',
            email       TEXT,
            phone       TEXT,
            is_active   INTEGER  NOT NULL DEFAULT 1,
            created_at  DATETIME DEFAULT (datetime('now','localtime')),
            updated_at  DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("""
            INSERT INTO users (username, password, full_name, role, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, ("admin", _hash("admin1234"), "System Administrator", "admin"))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════
# DECORATORS
# ══════════════════════════════════════════════

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("⛔ هذه الصفحة للمسؤولين فقط.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════

@users_bp.route("/")
@admin_required
def user_list():
    search = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "")

    db = get_db()
    query = "SELECT * FROM users WHERE 1=1"
    params = []

    if search:
        query += " AND (username LIKE ? OR full_name LIKE ? OR email LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if role_filter:
        query += " AND role = ?"
        params.append(role_filter)

    query += " ORDER BY created_at DESC"
    users = db.execute(query, params).fetchall()

    stats = db.execute("""
        SELECT
            COUNT(*)                                           AS total,
            SUM(CASE WHEN role='admin'      THEN 1 ELSE 0 END) AS admins,
            SUM(CASE WHEN role='pharmacist' THEN 1 ELSE 0 END) AS pharmacists,
            SUM(CASE WHEN role='doctor'     THEN 1 ELSE 0 END) AS doctors,
            SUM(CASE WHEN is_active=1       THEN 1 ELSE 0 END) AS active
        FROM users
    """).fetchone()
    db.close()

    return render_template_string(USER_LIST_TEMPLATE,
                                  users=users, stats=stats,
                                  search=search, role_filter=role_filter)


@users_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        data = {
            "username":  request.form.get("username", "").strip(),
            "password":  request.form.get("password", "").strip(),
            "full_name": request.form.get("full_name", "").strip(),
            "role":      request.form.get("role", "").strip(),
            "email":     request.form.get("email", "").strip(),
            "phone":     request.form.get("phone", "").strip(),
        }

        errors = []
        if not data["username"]:
            errors.append("اسم المستخدم مطلوب.")
        if len(data["password"]) < 6:
            errors.append("كلمة المرور يجب أن تكون 6 أحرف على الأقل.")
        if data["role"] not in ("admin", "pharmacist", "doctor"):
            errors.append("الدور غير صحيح.")
        if not data["full_name"]:
            errors.append("الاسم الكامل مطلوب.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template_string(USER_FORM_TEMPLATE, user=None, form_data=data)

        db = get_db()
        try:
            db.execute("""
                INSERT INTO users (username, password, full_name, role, email, phone)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data["username"], _hash(data["password"]),
                  data["full_name"], data["role"],
                  data["email"] or None, data["phone"] or None))
            db.commit()
            flash(f"✅ تم إضافة المستخدم «{data['full_name']}» بنجاح!", "success")
            return redirect(url_for("users.user_list"))
        except sqlite3.IntegrityError:
            flash("⚠️ اسم المستخدم مستخدم بالفعل.", "warning")
        finally:
            db.close()

    return render_template_string(USER_FORM_TEMPLATE, user=None, form_data={})


@users_bp.route("/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        db.close()
        flash("المستخدم غير موجود.", "danger")
        return redirect(url_for("users.user_list"))

    if request.method == "POST":
        data = {
            "full_name": request.form.get("full_name", "").strip(),
            "role":      request.form.get("role", "").strip(),
            "email":     request.form.get("email", "").strip(),
            "phone":     request.form.get("phone", "").strip(),
            "is_active": 1 if request.form.get("is_active") else 0,
            "new_pass":  request.form.get("new_password", "").strip(),
        }

        if data["new_pass"]:
            db.execute("""
                UPDATE users
                SET full_name=?, role=?, email=?, phone=?, is_active=?,
                    password=?, updated_at=datetime('now','localtime')
                WHERE id=?
            """, (data["full_name"], data["role"],
                  data["email"] or None, data["phone"] or None,
                  data["is_active"], _hash(data["new_pass"]), user_id))
        else:
            db.execute("""
                UPDATE users
                SET full_name=?, role=?, email=?, phone=?, is_active=?,
                    updated_at=datetime('now','localtime')
                WHERE id=?
            """, (data["full_name"], data["role"],
                  data["email"] or None, data["phone"] or None,
                  data["is_active"], user_id))

        db.commit()
        db.close()
        flash("✅ تم تحديث بيانات المستخدم بنجاح!", "success")
        return redirect(url_for("users.user_list"))

    db.close()
    return render_template_string(USER_FORM_TEMPLATE, user=user, form_data=dict(user))


@users_bp.route("/toggle/<int:user_id>", methods=["POST"])
@admin_required
def toggle_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user["is_active"] else 1
        db.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, user_id))
        db.commit()
        state_ar = "مفعّل" if new_status else "معطّل"
        flash(f"تم تغيير حالة «{user['full_name']}» إلى {state_ar}.", "info")
    db.close()
    return redirect(url_for("users.user_list"))


@users_bp.route("/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        flash(f"🗑️ تم حذف المستخدم «{user['full_name']}» نهائياً.", "danger")
    db.close()
    return redirect(url_for("users.user_list"))


# ══════════════════════════════════════════════
# TEMPLATES
# ══════════════════════════════════════════════

USER_LIST_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>إدارة المستخدمين</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <style>
    body { background:#f0f4f8; }
    .card { border:none; border-radius:16px; box-shadow:0 2px 12px rgba(0,0,0,.08); }
    .page-header { background:linear-gradient(135deg,#1a1a2e,#16213e); color:#fff; border-radius:16px; padding:1.5rem 2rem; margin-bottom:1.5rem; }
    .stat-card { border-radius:14px; padding:1.2rem 1.5rem; color:#fff; }
    .s1 { background:linear-gradient(135deg,#667eea,#764ba2); }
    .s2 { background:linear-gradient(135deg,#6f42c1,#9c27b0); }
    .s3 { background:linear-gradient(135deg,#0d6efd,#0dcaf0); }
    .s4 { background:linear-gradient(135deg,#198754,#20c997); }
    .s5 { background:linear-gradient(135deg,#fd7e14,#ffc107); }
    .badge-admin      { background:#6f42c1; }
    .badge-pharmacist { background:#0d6efd; }
    .badge-doctor     { background:#198754; }
    .action-btn { width:32px; height:32px; padding:0; display:inline-flex; align-items:center; justify-content:center; border-radius:8px; }
  </style>
</head>
<body>
<div class="container-fluid py-4 px-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} alert-dismissible fade show">{{ msg }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  {% endwith %}

  <div class="page-header d-flex justify-content-between align-items-center">
    <div>
      <h4 class="mb-1"><i class="fas fa-users me-2"></i>إدارة المستخدمين</h4>
      <small class="opacity-75">إضافة وتعديل وإدارة أدوار مستخدمي النظام</small>
    </div>
    <div class="d-flex gap-2">
      <a href="{{ url_for('dashboard') }}" class="btn btn-outline-light">
        <i class="fas fa-arrow-right me-1"></i> الرئيسية
      </a>
      <a href="{{ url_for('users.add_user') }}" class="btn btn-light">
        <i class="fas fa-user-plus me-1"></i> إضافة مستخدم
      </a>
    </div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-6 col-md-2"><div class="stat-card s1"><div class="fs-2 fw-bold">{{ stats.total }}</div><div class="small">الإجمالي</div></div></div>
    <div class="col-6 col-md-2"><div class="stat-card s2"><div class="fs-2 fw-bold">{{ stats.admins }}</div><div class="small">مسؤولون</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card s3"><div class="fs-2 fw-bold">{{ stats.pharmacists }}</div><div class="small">صيادلة</div></div></div>
    <div class="col-6 col-md-2"><div class="stat-card s4"><div class="fs-2 fw-bold">{{ stats.doctors }}</div><div class="small">أطباء</div></div></div>
    <div class="col-6 col-md-3"><div class="stat-card s5"><div class="fs-2 fw-bold">{{ stats.active }}</div><div class="small">نشطون</div></div></div>
  </div>

  <div class="card mb-4">
    <div class="card-body">
      <form method="get" class="row g-2 align-items-end">
        <div class="col-md-6">
          <input type="text" name="q" class="form-control" placeholder="بحث باسم أو يوزرنيم…" value="{{ search }}">
        </div>
        <div class="col-md-3">
          <select name="role" class="form-select">
            <option value="">كل الأدوار</option>
            <option value="admin"      {% if role_filter=='admin'      %}selected{% endif %}>مسؤول</option>
            <option value="pharmacist" {% if role_filter=='pharmacist' %}selected{% endif %}>صيدلي</option>
            <option value="doctor"     {% if role_filter=='doctor'     %}selected{% endif %}>طبيب</option>
          </select>
        </div>
        <div class="col-md-3">
          <button type="submit" class="btn btn-primary w-100"><i class="fas fa-search me-1"></i> بحث</button>
        </div>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="card-body p-0">
      <table class="table table-hover align-middle mb-0">
        <thead>
          <tr>
            <th>#</th><th>الاسم الكامل</th><th>اسم المستخدم</th>
            <th>الدور</th><th>الإيميل</th><th>الحالة</th><th>إجراءات</th>
          </tr>
        </thead>
        <tbody>
          {% for u in users %}
          <tr>
            <td class="text-muted small">{{ u.id }}</td>
            <td class="fw-semibold">{{ u.full_name or '—' }}</td>
            <td><code>{{ u.username }}</code></td>
            <td>
              {% if u.role == 'admin' %}<span class="badge badge-admin">مسؤول</span>
              {% elif u.role == 'pharmacist' %}<span class="badge badge-pharmacist">صيدلي</span>
              {% else %}<span class="badge badge-doctor">طبيب</span>{% endif %}
            </td>
            <td class="small">{{ u.email or '—' }}</td>
            <td>
              {% if u.is_active %}<span class="badge bg-success">نشط</span>
              {% else %}<span class="badge bg-secondary">معطّل</span>{% endif %}
            </td>
            <td>
              <div class="d-flex gap-1">
                <a href="{{ url_for('users.edit_user', user_id=u.id) }}"
                   class="btn btn-sm btn-outline-primary action-btn" title="تعديل">
                  <i class="fas fa-edit fa-xs"></i>
                </a>
                <form method="post" action="{{ url_for('users.toggle_user', user_id=u.id) }}" class="d-inline">
                  <button type="submit" class="btn btn-sm action-btn {% if u.is_active %}btn-outline-warning{% else %}btn-outline-success{% endif %}">
                    <i class="fas {% if u.is_active %}fa-ban{% else %}fa-check{% endif %} fa-xs"></i>
                  </button>
                </form>
                <form method="post" action="{{ url_for('users.delete_user', user_id=u.id) }}" class="d-inline"
                      onsubmit="return confirm('هل أنت متأكد من حذف هذا المستخدم؟')">
                  <button type="submit" class="btn btn-sm btn-outline-danger action-btn">
                    <i class="fas fa-trash fa-xs"></i>
                  </button>
                </form>
              </div>
            </td>
          </tr>
          {% else %}
          <tr><td colspan="7" class="text-center py-4 text-muted">لا يوجد مستخدمون</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="card-footer text-muted small">إجمالي النتائج: <strong>{{ users|length }}</strong></div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

USER_FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>{% if user %}تعديل مستخدم{% else %}إضافة مستخدم{% endif %}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
  <style>
    body { background:#f0f4f8; }
    .card { border:none; border-radius:16px; box-shadow:0 2px 12px rgba(0,0,0,.08); }
  </style>
</head>
<body>
<div class="container py-4">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }} alert-dismissible fade show">{{ msg }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  {% endwith %}

  <div class="row justify-content-center">
    <div class="col-lg-6">
      <div class="card">
        <div class="card-header py-3">
          <h5 class="mb-0">
            <i class="fas {% if user %}fa-user-edit{% else %}fa-user-plus{% endif %} me-2 text-primary"></i>
            {% if user %}تعديل بيانات المستخدم{% else %}إضافة مستخدم جديد{% endif %}
          </h5>
        </div>
        <div class="card-body">
          <form method="post">

            <div class="mb-3">
              <label class="form-label fw-semibold">الاسم الكامل <span class="text-danger">*</span></label>
              <input type="text" name="full_name" class="form-control"
                     value="{{ form_data.get('full_name','') }}" required>
            </div>

            {% if not user %}
            <div class="mb-3">
              <label class="form-label fw-semibold">اسم المستخدم <span class="text-danger">*</span></label>
              <input type="text" name="username" class="form-control"
                     value="{{ form_data.get('username','') }}" required>
            </div>
            {% else %}
            <div class="mb-3">
              <label class="form-label fw-semibold">اسم المستخدم</label>
              <input type="text" class="form-control" value="{{ user.username }}" disabled>
            </div>
            {% endif %}

            <div class="mb-3">
              <label class="form-label fw-semibold">الدور <span class="text-danger">*</span></label>
              <select name="role" class="form-select" required>
                <option value="">-- اختر الدور --</option>
                <option value="admin"      {% if form_data.get('role')=='admin'      %}selected{% endif %}>مسؤول (Admin)</option>
                <option value="pharmacist" {% if form_data.get('role')=='pharmacist' %}selected{% endif %}>صيدلي (Pharmacist)</option>
                <option value="doctor"     {% if form_data.get('role')=='doctor'     %}selected{% endif %}>طبيب (Doctor)</option>
              </select>
            </div>

            <div class="mb-3">
              <label class="form-label fw-semibold">
                {% if user %}كلمة مرور جديدة (اتركه فارغاً للإبقاء على القديمة)
                {% else %}كلمة المرور <span class="text-danger">*</span>{% endif %}
              </label>
              <div class="input-group">
                <input type="password" name="{% if user %}new_password{% else %}password{% endif %}"
                       class="form-control" id="passInput"
                       {% if not user %}required minlength="6"{% endif %}
                       placeholder="6 أحرف على الأقل">
                <button class="btn btn-outline-secondary" type="button" onclick="togglePass()">
                  <i class="fas fa-eye" id="passIcon"></i>
                </button>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label fw-semibold">البريد الإلكتروني</label>
              <input type="email" name="email" class="form-control"
                     value="{{ form_data.get('email','') }}">
            </div>

            <div class="mb-3">
              <label class="form-label fw-semibold">رقم الهاتف</label>
              <input type="tel" name="phone" class="form-control"
                     value="{{ form_data.get('phone','') }}">
            </div>

            {% if user %}
            <div class="mb-4">
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" name="is_active" id="isActive"
                       {% if form_data.get('is_active', user.is_active) %}checked{% endif %}>
                <label class="form-check-label fw-semibold" for="isActive">الحساب نشط</label>
              </div>
            </div>
            {% endif %}

            <div class="d-flex gap-2">
              <button type="submit" class="btn btn-primary px-4">
                <i class="fas fa-save me-1"></i>
                {% if user %}حفظ التعديلات{% else %}إضافة المستخدم{% endif %}
              </button>
              <a href="{{ url_for('users.user_list') }}" class="btn btn-outline-secondary px-4">إلغاء</a>
            </div>

          </form>
        </div>
      </div>
    </div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
function togglePass() {
  const inp = document.getElementById('passInput');
  const icon = document.getElementById('passIcon');
  if (inp.type === 'password') { inp.type = 'text'; icon.classList.replace('fa-eye','fa-eye-slash'); }
  else { inp.type = 'password'; icon.classList.replace('fa-eye-slash','fa-eye'); }
}
</script>
</body>
</html>
"""