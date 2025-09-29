
import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for, send_from_directory, session,
    abort, flash, render_template_string
)
from werkzeug.utils import secure_filename

# ---------- Settings ----------
APP_TITLE = "منصة الواجبات والدرجات"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

# Set secrets via environment variables in production
ADMIN_CODE = os.environ.get("ADMIN_CODE", "change-me-ostad-code")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-secret-key")

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = SECRET_KEY
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- Database ----------
DB_PATH = os.path.join(os.path.dirname(__file__), "school.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    grade TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
);
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

with get_db() as conn:
    conn.executescript(SCHEMA)
    conn.commit()

# ---------- Base HTML ----------
BASE_HTML = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title or app_title }}</title>
<style>
  body {font-family: system-ui, Tahoma, Arial; background:#f5f7fb; margin:0}
  header {background:#3b82f6; color:white; padding:16px}
  header .wrap, main .wrap {max-width: 1000px; margin: 0 auto}
  a {color:#1f2937; text-decoration:none}
  .card {background:white; border-radius:18px; padding:18px; margin:16px 0; box-shadow:0 6px 18px rgba(0,0,0,.06)}
  .btn {display:inline-block; padding:10px 16px; border-radius:12px; border:1px solid #cbd5e1; background:#111827; color:white}
  .btn.secondary{ background:#f1f5f9; color:#111827 }
  .grid {display:grid; gap:12px}
  .grid.two {grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));}
  input, select {width:100%; padding:10px; border-radius:10px; border:1px solid #cbd5e1}
  table {width:100%; border-collapse:collapse}
  th, td {padding:10px; border-bottom:1px solid #e5e7eb; text-align:right}
  .muted {color:#6b7280}
  .topbar {display:flex; gap:12px; align-items:center; justify-content:space-between}
  .tag {background:#e0e7ff; color:#1e3a8a; padding:4px 8px; border-radius:999px; font-size:12px}
  .flash {background:#fff7ed; border:1px solid #fed7aa; padding:10px; border-radius:10px; margin:10px 0}
</style>
</head>
<body>
<header>
  <div class="wrap topbar">
    <div><strong>{{ app_title }}</strong></div>
    <nav>
      {% if session.get('student_name') %}
        <span class="tag">مرحبًا، {{ session['student_name'] }}</span>
        <a class="btn secondary" href="{{ url_for('logout') }}">خروج</a>
      {% elif session.get('is_admin') %}
        <span class="tag">الأستاذ</span>
        <a class="btn secondary" href="{{ url_for('admin_dashboard') }}">لوحة التحكم</a>
        <a class="btn secondary" href="{{ url_for('logout') }}">خروج</a>
      {% else %}
        <a class="btn secondary" href="{{ url_for('admin_login') }}">دخول الأستاذ</a>
      {% endif %}
    </nav>
  </div>
</header>
<main>
  <div class="wrap">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
      {% endif %}
    {% endwith %}
    {{ content|safe }}
  </div>
</main>
</body>
</html>
"""

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    with get_db() as conn:
        files = conn.execute("SELECT * FROM files ORDER BY id DESC").fetchall()
    content = """
    <div class="card">
      <h2>تسجيل دخول التلميذ</h2>
      <p class="muted">أدخل الكود الخاص بك للاطلاع على الدرجات والواجبات.</p>
      <form method="post" action="{{ url_for('student_login') }}" class="grid two">
        <div>
          <label>الكود</label>
          <input type="text" name="code" required placeholder="مثال: 8392" />
        </div>
        <div style="align-self:end">
          <button class="btn" type="submit">دخول</button>
        </div>
      </form>
    </div>

    <div class="card">
      <h3>الواجبات والملفات المتاحة للجميع</h3>
      <table>
        <thead><tr><th>العنوان</th><th>التاريخ</th><th>تحميل</th></tr></thead>
        <tbody>
        {% for f in files %}
          <tr>
            <td>{{ f['title'] }}</td>
            <td class="muted">{{ f['uploaded_at'] }}</td>
            <td><a class="btn secondary" href="{{ url_for('download_file', file_id=f['id']) }}">تنزيل</a></td>
          </tr>
        {% else %}
          <tr><td colspan="3" class="muted">لا توجد ملفات بعد.</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    """
    return render_template_string(BASE_HTML, app_title=APP_TITLE, title=APP_TITLE,
                                  content=render_template_string(content, files=files))

@app.post("/login")
def student_login():
    code = request.form.get("code", "").strip()
    with get_db() as conn:
        st = conn.execute("SELECT * FROM students WHERE code=?", (code,)).fetchone()
    if not st:
        flash("الكود غير صحيح.")
        return redirect(url_for("index"))
    session.clear()
    session["student_id"] = st["id"]
    session["student_name"] = st["name"]
    return redirect(url_for("student_dashboard"))

@app.get("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج.")
    return redirect(url_for("index"))

@app.get("/dashboard")
def student_dashboard():
    if not session.get("student_id"):
        return redirect(url_for("index"))
    sid = session["student_id"]
    with get_db() as conn:
        grades = conn.execute(
            "SELECT subject, grade, COALESCE(note, '') AS note, created_at FROM grades WHERE student_id=? ORDER BY id DESC",
            (sid,)
        ).fetchall()
        files = conn.execute("SELECT * FROM files ORDER BY id DESC").fetchall()
    content = """
    <div class="card">
      <h2>درجاتي</h2>
      <table>
        <thead><tr><th>المادة</th><th>الدرجة</th><th>ملاحظة</th><th>التاريخ</th></tr></thead>
        <tbody>
        {% for g in grades %}
          <tr>
            <td>{{ g['subject'] }}</td>
            <td><strong>{{ g['grade'] }}</strong></td>
            <td>{{ g['note'] }}</td>
            <td class="muted">{{ g['created_at'] }}</td>
          </tr>
        {% else %}
          <tr><td colspan="4" class="muted">لا توجد درجات حتى الآن.</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h3>الواجبات والملفات</h3>
      <table>
        <thead><tr><th>العنوان</th><th>التاريخ</th><th>تحميل</th></tr></thead>
        <tbody>
        {% for f in files %}
          <tr>
            <td>{{ f['title'] }}</td>
            <td class="muted">{{ f['uploaded_at'] }}</td>
            <td><a class="btn secondary" href="{{ url_for('download_file', file_id=f['id']) }}">تنزيل</a></td>
          </tr>
        {% else %}
          <tr><td colspan="3" class="muted">لا توجد ملفات بعد.</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    """
    return render_template_string(BASE_HTML, app_title=APP_TITLE, title="لوحتي",
                                  content=render_template_string(content, grades=grades, files=files))

@app.get("/download/<int:file_id>")
def download_file(file_id):
    with get_db() as conn:
        f = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if not f:
        abort(404)
    filepath = os.path.join(UPLOAD_FOLDER, f["filename"])
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], f['filename'], as_attachment=True)

# ---------- Admin (الأستاذ) ----------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if code == ADMIN_CODE:
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("كود الأستاذ غير صحيح.")
        return redirect(url_for("admin_login"))

    content = """
    <div class="card">
      <h2>دخول الأستاذ</h2>
      <form method="post" class="grid two">
        <div>
          <label>كود الأستاذ</label>
          <input type="password" name="code" required />
        </div>
        <div style="align-self:end">
          <button class="btn" type="submit">دخول</button>
        </div>
      </form>
    </div>
    "
    """
    return render_template_string(BASE_HTML, app_title=APP_TITLE, title="دخول الأستاذ",
                                  content=content)

@app.get("/admin/dashboard")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    with get_db() as conn:
        students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
        files = conn.execute("SELECT * FROM files ORDER BY id DESC").fetchall()
    content = """
    <div class="card">
      <h2>لوحة التحكم</h2>
      <div class="grid two">
        <div>
          <h3>إضافة / إدارة التلاميذ</h3>
          <form method="post" action="{{ url_for('admin_add_student') }}" class="grid two">
            <div>
              <label>الاسم</label>
              <input type="text" name="name" required placeholder="مثال: أحمد علي" />
            </div>
            <div>
              <label>الكود</label>
              <input type="text" name="code" required placeholder="مثال: 8392" />
            </div>
            <div style="grid-column:1 / -1; text-align:left">
              <button class="btn" type="submit">حفظ التلميذ</button>
            </div>
          </form>

          <h4>التلاميذ</h4>
          <table>
            <thead><tr><th>الاسم</th><th>الكود</th><th>إضافة درجة</th></tr></thead>
            <tbody>
            {% for s in students %}
              <tr>
                <td>{{ s['name'] }}</td>
                <td><code>{{ s['code'] }}</code></td>
                <td>
                  <form method="post" action="{{ url_for('admin_add_grade', student_id=s['id']) }}" class="grid two">
                    <input type="text" name="subject" placeholder="المادة" required />
                    <input type="text" name="grade" placeholder="الدرجة" required />
                    <input type="text" name="note" placeholder="ملاحظة (اختياري)" />
                    <button class="btn" type="submit">إضافة</button>
                  </form>
                </td>
              </tr>
            {% else %}
              <tr><td colspan="3" class="muted">لا يوجد تلاميذ.</td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>

        <div>
          <h3>رفع الواجبات/الملفات (PDF / Word)</h3>
          <form method="post" action="{{ url_for('admin_upload') }}" enctype="multipart/form-data" class="grid two">
            <input type="text" name="title" placeholder="عنوان الملف" required />
            <input type="file" name="file" accept=".pdf,.doc,.docx" required />
            <div style="grid-column:1 / -1; text-align:left">
              <button class="btn" type="submit">رفع</button>
            </div>
          </form>

          <h4>الملفات</h4>
          <table>
            <thead><tr><th>العنوان</th><th>الاسم</th><th>التاريخ</th></tr></thead>
            <tbody>
            {% for f in files %}
              <tr>
                <td>{{ f['title'] }}</td>
                <td class="muted">{{ f['filename'] }}</td>
                <td class="muted">{{ f['uploaded_at'] }}</td>
              </tr>
            {% else %}
              <tr><td colspan="3" class="muted">لا توجد ملفات.</td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """
    return render_template_string(BASE_HTML, app_title=APP_TITLE, title="لوحة التحكم",
                                  content=render_template_string(content, students=students, files=files))

@app.post("/admin/student/add")
def admin_add_student():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    if not name or not code:
        flash("الاسم والكود مطلوبان.")
        return redirect(url_for("admin_dashboard"))
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO students (name, code) VALUES (?, ?)", (name, code))
            conn.commit()
        flash("تمت إضافة التلميذ بنجاح.")
    except sqlite3.IntegrityError:
        flash("هذا الكود مستخدم بالفعل، اختر كودًا آخر.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/grade/add/<int:student_id>")
def admin_add_grade(student_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    subject = request.form.get("subject", "").strip()
    grade = request.form.get("grade", "").strip()
    note = request.form.get("note", "").strip() or None
    if not subject or not grade:
        flash("المادة والدرجة مطلوبتان.")
        return redirect(url_for("admin_dashboard"))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO grades (student_id, subject, grade, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (student_id, subject, grade, note, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
    flash("تمت إضافة الدرجة.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/upload")
def admin_upload():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    title = request.form.get("title", "").strip()
    file = request.files.get("file")
    if not title or not file:
        flash("العنوان والملف مطلوبان.")
        return redirect(url_for("admin_dashboard"))
    if not allowed_file(file.filename):
        flash("صيغة الملف غير مسموحة. المسموح: PDF, DOC, DOCX")
        return redirect(url_for("admin_dashboard"))
    fname = secure_filename(file.filename)
    base, ext = os.path.splitext(fname)
    fname = f"{base}_{int(datetime.now().timestamp())}{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, fname))
    with get_db() as conn:
        conn.execute(
            "INSERT INTO files (title, filename, uploaded_at) VALUES (?, ?, ?)",
            (title, fname, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
    flash("تم رفع الملف.")
    return redirect(url_for("admin_dashboard"))

@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline';"
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
