# موقع الأستاذ بن أحمد — ثانوية الشهيد طيبي محمد
# نسخة ملف واحد (Flask) — تعمل محليًا أو على Render

import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, request, redirect, url_for, send_from_directory, session,
    abort, flash, render_template_string
)
from werkzeug.utils import secure_filename

# --------------------- إعدادات ---------------------
APP_TITLE = "موقع الأستاذ بن أحمد"
SCHOOL_NAME = "ثانوية الشهيد طيبي محمد"

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

ADMIN_CODE = os.environ.get("ADMIN_CODE", "ostad123")  # كود الأستاذ
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")

# الأفواج/الأقسام
CLASS_CHOICES = ["2 ع 1", "3 ع"]

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = SECRET_KEY
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------- قاعدة البيانات ---------------------
DB_PATH = os.path.join(os.getcwd(), "school.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE,
    class_group TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    class_group TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
);

-- القيم قد تكون فارغة، والمعدل يُحسب فقط عند اكتمالها
CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    ca REAL,        -- نقطة التقويم المستمر
    t1 REAL,        -- الفرض الأول
    t2 REAL,        -- الفرض الثاني
    exam REAL,      -- الإختبار
    created_at TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(id)
);
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

with get_db() as conn:
    conn.executescript(SCHEMA)
    conn.commit()

# --------------------- القالب العام ---------------------
BASE_HTML = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title or app_title }}</title>
<style>
  body {font-family: system-ui, Tahoma, Arial; background:#f5f7fb; margin:0}
  header {background:#16a34a; color:white; padding:16px}
  header .wrap, main .wrap {max-width: 1000px; margin: 0 auto}
  a {color:#1f2937; text-decoration:none}
  .card {background:white; border-radius:18px; padding:18px; margin:16px 0; box-shadow:0 6px 18px rgba(0,0,0,.06)}
  .btn {display:inline-block; padding:10px 16px; border-radius:12px; border:1px solid #cbd5e1; background:#111827; color:white; cursor:pointer}
  .btn.secondary{ background:#f1f5f9; color:#111827 }
  .btn.danger{ background:#b91c1c; border-color:#fca5a5 }
  .grid {display:grid; gap:12px}
  .grid.two {grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));}
  input, select {width:100%; padding:10px; border-radius:10px; border:1px solid #cbd5e1}
  table {width:100%; border-collapse:collapse}
  th, td {padding:10px; border-bottom:1px solid #e5e7eb; text-align:right}
  .muted {color:#6b7280}
  .topbar {display:flex; gap:12px; align-items:center; justify-content:space-between}
  .tag {background:#dcfce7; color:#065f46; padding:4px 8px; border-radius:999px; font-size:12px}
  .flash {background:#fff7ed; border:1px solid #fed7aa; padding:10px; border-radius:10px; margin:10px 0; color:#7c2d12}
  .subtitle {font-size:13px; opacity:.95}
</style>
</head>
<body>
<header>
  <div class="wrap topbar">
    <div>
      <div><strong>{{ app_title }}</strong></div>
      <div class="subtitle">{{ school_name }}</div>
    </div>
    <nav>
      {% if session.get('student_name') %}
        <span class="tag">مرحبًا، {{ session['student_name'] }} — {{ session['class_group'] }}</span>
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

# --------------------- الصفحة الرئيسية ---------------------
@app.route("/")
def index():
    content = """
    <div class="card">
      <h2>تسجيل دخول التلميذ</h2>
      <form method="post" action="{{ url_for('student_login') }}" class="grid two">
        <div>
          <label>الكود</label>
          <input type="text" name="code" required placeholder="مثال: 8392" />
        </div>
        <div>
          <label>القسم / الفوج</label>
          <select name="class_group" required>
            <option value="" disabled selected>اختر الفوج</option>
            {% for c in class_choices %}
              <option value="{{ c }}">{{ c }}</option>
            {% endfor %}
          </select>
        </div>
        <div style="grid-column:1 / -1; text-align:left">
          <button class="btn" type="submit">دخول</button>
        </div>
      </form>
    </div>
    """
    return render_template_string(
        BASE_HTML, app_title=APP_TITLE, school_name=SCHOOL_NAME, title=APP_TITLE,
        content=render_template_string(content, class_choices=CLASS_CHOICES)
    )

@app.post("/login")
def student_login():
    code = request.form.get("code", "").strip()
    class_group = request.form.get("class_group", "").strip()
    if not class_group:
        flash("فضلاً اختر الفوج.")
        return redirect(url_for("index"))
    with get_db() as conn:
        st = conn.execute(
            "SELECT * FROM students WHERE code=? AND class_group=?",
            (code, class_group)
        ).fetchone()
    if not st:
        flash("الكود أو الفوج غير صحيح.")
        return redirect(url_for("index"))
    session.clear()
    session["student_id"] = st["id"]
    session["student_name"] = st["name"]
    session["class_group"] = st["class_group"]
    return redirect(url_for("student_dashboard"))

@app.get("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج.")
    return redirect(url_for("index"))

# --------------------- لوحة التلميذ ---------------------
@app.get("/dashboard")
def student_dashboard():
    if not session.get("student_id"):
        return redirect(url_for("index"))
    sid = session["student_id"]
    sgroup = session.get("class_group")
    with get_db() as conn:
        assessments = conn.execute(
            "SELECT subject, ca, t1, t2, exam, created_at FROM assessments WHERE student_id=? ORDER BY id DESC",
            (sid,)
        ).fetchall()
        files = conn.execute(
            "SELECT * FROM files WHERE class_group=? ORDER BY id DESC",
            (sgroup,)
        ).fetchall()
        student = conn.execute("SELECT name FROM students WHERE id=?", (sid,)).fetchone()

    rows = []
    for a in assessments:
        ca = a["ca"] if a["ca"] is not None else None
        t1 = a["t1"] if a["t1"] is not None else None
        t2 = a["t2"] if a["t2"] is not None else None
        exam = a["exam"] if a["exam"] is not None else None
        final_avg = None
        if ca is not None and t1 is not None and t2 is not None and exam is not None:
            avg_tests = (float(t1) + float(t2)) / 2.0
            final_avg = round((float(ca) + avg_tests + (float(exam) * 2)) / 4.0, 2)
        rows.append({
            "subject": a["subject"],
            "ca": ca, "t1": t1, "t2": t2, "exam": exam,
            "final": final_avg, "created_at": a["created_at"]
        })

    content = """
    <div class="card">
      <h2>البيانات الدراسية</h2>
      <table>
        <thead>
          <tr>
            <th>الإسم و اللقب</th>
            <th>المادة</th>
            <th>نقطة التقويم المستمر</th>
            <th>الفرض الأول</th>
            <th>الفرض الثاني</th>
            <th>الإختبار</th>
            <th>المعدل</th>
          </tr>
        </thead>
        <tbody>
          {% for r in rows %}
            <tr>
              <td>{{ student_name }}</td>
              <td>{{ r.subject }}</td>
              <td>{{ r.ca if r.ca is not none else '—' }}</td>
              <td>{{ r.t1 if r.t1 is not none else '—' }}</td>
              <td>{{ r.t2 if r.t2 is not none else '—' }}</td>
              <td>{{ r.exam if r.exam is not none else '—' }}</td>
              <td><strong>{{ r.final if r.final is not none else '—' }}</strong></td>
            </tr>
          {% else %}
            <tr><td colspan="7" class="muted">لا توجد بيانات لحد الآن.</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h3>واجباتي / ملفاتي ({{ class_group }})</h3>
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
    return render_template_string(
        BASE_HTML, app_title=APP_TITLE, school_name=SCHOOL_NAME, title="لوحتي",
        content=render_template_string(content, rows=rows, files=files,
                                       class_group=sgroup, student_name=student["name"])
    )

# --------------------- تنزيل ملف ---------------------
@app.get("/download/<int:file_id>")
def download_file(file_id):
    if not session.get("student_id") and not session.get("is_admin"):
        flash("فضلاً سجّل الدخول أولاً.")
        return redirect(url_for("index"))
    with get_db() as conn:
        f = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if not f:
        abort(404)
    if session.get("student_id") and f["class_group"] != session.get("class_group"):
        abort(403)
    filepath = os.path.join(UPLOAD_FOLDER, f["filename"])
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], f['filename'], as_attachment=True)

# --------------------- دخول الأستاذ ---------------------
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
    """
    return render_template_string(BASE_HTML, app_title=APP_TITLE, school_name=SCHOOL_NAME,
                                  title="دخول الأستاذ", content=content)

# --------------------- لوحة الأستاذ ---------------------
@app.get("/admin/dashboard")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    with get_db() as conn:
        students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
        files = conn.execute("SELECT * FROM files ORDER BY id DESC").fetchall()
        last_assess = conn.execute(
            """SELECT assessments.*, students.name AS sname
               FROM assessments JOIN students ON students.id=assessments.student_id
               ORDER BY assessments.id DESC LIMIT 10"""
        ).fetchall()

    content = """
    <div class="card">
      <h2>لوحة التحكم</h2>
      <div class="grid two">
        <div>
          <h3>إضافة / إدارة التلاميذ</h3>
          <form method="post" action="{{ url_for('admin_add_student') }}" class="grid two">
            <div>
              <label>الإسم و اللقب</label>
              <input type="text" name="name" required placeholder="مثال: أحمد بن علي" />
            </div>
            <div>
              <label>الكود</label>
              <input type="text" name="code" required placeholder="مثال: 8392" />
            </div>
            <div>
              <label>القسم / الفوج</label>
              <select name="class_group" required>
                {% for c in class_choices %}
                  <option value="{{ c }}">{{ c }}</option>
                {% endfor %}
              </select>
            </div>
            <div style="grid-column:1 / -1; text-align:left">
              <button class="btn" type="submit">حفظ التلميذ</button>
            </div>
          </form>

          <h4>التلاميذ</h4>
          <table>
            <thead>
              <tr>
                <th>الإسم و اللقب</th><th>الكود</th><th>الفوج</th>
                <th>إضافة تقييم/اختبار</th><th>حذف</th>
              </tr>
            </thead>
            <tbody>
            {% for s in students %}
              <tr>
                <td>{{ s['name'] }}</td>
                <td><code>{{ s['code'] }}</code></td>
                <td>{{ s['class_group'] }}</td>
                <td>
                  <form method="post" action="{{ url_for('admin_add_assessment', student_id=s['id']) }}" class="grid two">
                    <input type="text" name="subject" placeholder="المادة" required />
                    <input type="number" step="0.01" name="ca"   placeholder="التقويم (اختياري)" />
                    <input type="number" step="0.01" name="t1"   placeholder="الفرض 1 (اختياري)" />
                    <input type="number" step="0.01" name="t2"   placeholder="الفرض 2 (اختياري)" />
                    <input type="number" step="0.01" name="exam" placeholder="الإختبار (اختياري)" />
                    <button class="btn" type="submit">حفظ / تحديث</button>
                  </form>
                </td>
                <td>
                  <form method="post"
                        action="{{ url_for('admin_delete_student', student_id=s['id']) }}"
                        onsubmit="return confirm('تأكيد حذف هذا العنصر؟');">
                    <button class="btn danger" type="submit">حذف التلميذ</button>
                  </form>
                </td>
              </tr>
            {% else %}
              <tr><td colspan="5" class="muted">لا يوجد تلاميذ.</td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>

        <div>
          <h3>رفع الواجبات/الملفات (حسب الفوج)</h3>
          <form method="post" action="{{ url_for('admin_upload') }}" enctype="multipart/form-data" class="grid two">
            <input type="text" name="title" placeholder="عنوان الملف" required />
            <input type="file" name="file" accept=".pdf,.doc,.docx" required />
            <div>
              <label>القسم / الفوج</label>
              <select name="class_group" required>
                {% for c in class_choices %}
                  <option value="{{ c }}">{{ c }}</option>
                {% endfor %}
              </select>
            </div>
            <div style="grid-column:1 / -1; text-align:left">
              <button class="btn" type="submit">رفع</button>
            </div>
          </form>

          <h4>الملفات</h4>
          <table>
            <thead>
              <tr>
                <th>العنوان</th><th>الفوج</th><th>الاسم</th><th>التاريخ</th><th>حذف</th>
              </tr>
            </thead>
            <tbody>
            {% for f in files %}
              <tr>
                <td>{{ f['title'] }}</td>
                <td>{{ f['class_group'] }}</td>
                <td class="muted">{{ f['filename'] }}</td>
                <td class="muted">{{ f['uploaded_at'] }}</td>
                <td>
                  <form method="post"
                        action="{{ url_for('admin_delete_file', file_id=f['id']) }}"
                        onsubmit="return confirm('تأكيد حذف هذا العنصر؟');">
                    <button class="btn secondary" type="submit">حذف</button>
                  </form>
                </td>
              </tr>
            {% else %}
              <tr><td colspan="5" class="muted">لا توجد ملفات.</td></tr>
            {% endfor %}
            </tbody>
          </table>

          <h4>آخر القيّمات المُضافة</h4>
          <table>
            <thead><tr><th>التلميذ</th><th>المادة</th><th>تقويم</th><th>فرض1</th><th>فرض2</th><th>اختبار</th><th>تاريخ</th></tr></thead>
            <tbody>
            {% for a in last_assess %}
              <tr>
                <td>{{ a['sname'] }}</td>
                <td>{{ a['subject'] }}</td>
                <td>{{ a['ca'] if a['ca'] is not none else '—' }}</td>
                <td>{{ a['t1'] if a['t1'] is not none else '—' }}</td>
                <td>{{ a['t2'] if a['t2'] is not none else '—' }}</td>
                <td>{{ a['exam'] if a['exam'] is not none else '—' }}</td>
                <td class="muted">{{ a['created_at'] }}</td>
              </tr>
            {% else %}
              <tr><td colspan="7" class="muted">لا شيء بعد.</td></tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """
    return render_template_string(
        BASE_HTML, app_title=APP_TITLE, school_name=SCHOOL_NAME, title="لوحة التحكم",
        content=render_template_string(content, students=students, files=files,
                                      last_assess=last_assess, class_choices=CLASS_CHOICES)
    )

# --------------------- إجراءات الأستاذ ---------------------
@app.post("/admin/student/add")
def admin_add_student():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    class_group = request.form.get("class_group", "").strip()
    if not name or not code or not class_group:
        flash("الاسم والكود والفوج مطلوبة.")
        return redirect(url_for("admin_dashboard"))
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO students (name, code, class_group) VALUES (?, ?, ?)",
                         (name, code, class_group))
            conn.commit()
        flash("تمت إضافة التلميذ بنجاح.")
    except sqlite3.IntegrityError:
        flash("هذا الكود مستخدم بالفعل، اختر كودًا آخر.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/assessment/add/<int:student_id>")
def admin_add_assessment(student_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    subject = request.form.get("subject", "").strip()

    def parse_optional(name):
        v = request.form.get(name, "").strip()
        if v == "":
            return None
        try:
            return float(v)
        except ValueError:
            return None

    ca = parse_optional("ca")
    t1 = parse_optional("t1")
    t2 = parse_optional("t2")
    exam = parse_optional("exam")

    if not subject:
        flash("المادة مطلوبة.")
        return redirect(url_for("admin_dashboard"))

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, ca, t1, t2, exam FROM assessments WHERE student_id=? AND subject=?",
            (student_id, subject)
        ).fetchone()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        if existing:
            new_ca   = ca   if ca   is not None else existing["ca"]
            new_t1   = t1   if t1   is not None else existing["t1"]
            new_t2   = t2   if t2   is not None else existing["t2"]
            new_exam = exam if exam is not None else existing["exam"]
            conn.execute(
                "UPDATE assessments SET ca=?, t1=?, t2=?, exam=?, created_at=? WHERE id=?",
                (new_ca, new_t1, new_t2, new_exam, now, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO assessments (student_id, subject, ca, t1, t2, exam, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (student_id, subject, ca, t1, t2, exam, now)
            )
        conn.commit()
    flash("تم حفظ/تحديث القيّمات.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/upload")
def admin_upload():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    title = request.form.get("title", "").strip()
    class_group = request.form.get("class_group", "").strip()
    file = request.files.get("file")
    if not title or not file or not class_group:
        flash("العنوان والملف والفوج مطلوبة.")
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
            "INSERT INTO files (title, filename, class_group, uploaded_at) VALUES (?, ?, ?, ?)",
            (title, fname, class_group, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
    flash("تم رفع الملف.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/student/delete/<int:student_id>")
def admin_delete_student(student_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    with get_db() as conn:
        conn.execute("DELETE FROM assessments WHERE student_id=?", (student_id,))
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
        conn.commit()
    flash("تم حذف التلميذ وجميع تقييماته.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/file/delete/<int:file_id>")
def admin_delete_file(file_id):
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    with get_db() as conn:
        f = conn.execute("SELECT filename FROM files WHERE id=?", (file_id,)).fetchone()
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
    if f:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, f["filename"]))
        except FileNotFoundError:
            pass
    flash("تم حذف الملف.")
    return redirect(url_for("admin_dashboard"))

# --------------------- أمان الرؤوس ---------------------
@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline';"
    return resp

# تشغيل محليًا: python app.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
