from flask import Flask, render_template, request, redirect, send_from_directory, abort, session
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret")

# ---------- PATH SETUP (RENDER SAFE) ----------
UPLOAD_FOLDER = "/tmp/uploads"
DB_PATH = "/tmp/projects.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- DATABASE INIT ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        file TEXT,
        type TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS auth(
        id INTEGER PRIMARY KEY,
        pin TEXT,
        email TEXT
    )
    """)

    c.execute("""
    INSERT OR IGNORE INTO auth(id,pin,email)
    VALUES(1,'1234','admin@email.com')
    """)

    conn.commit()
    conn.close()


@app.before_request
def initialize_db_once():
    if not hasattr(app, "db_initialized"):
        init_db()
        app.db_initialized = True


# ---------- DASHBOARD ----------
@app.route("/")
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return render_template("dashboard.html", projects=projects)


# ---------- IMAGE AR ----------
@app.route("/image-ar/<filename>")
def image_ar(filename):
    return render_template("image_ar.html", filename=filename)


# ---------- MODEL AR ----------
@app.route("/model-ar/<filename>")
def model_ar(filename):
    return render_template("model_ar.html", file=filename)


# ---------- CREATE PROJECT ----------
@app.route("/create")
def create_project():
    if not session.get("create_auth"):
        return render_template("pin_login.html", next_page="/create")
    return render_template("create_project.html")


# ---------- VERIFY PIN ----------
@app.route("/verify-pin", methods=["POST"])
def verify_pin():
    pin = request.form.get("pin")
    next_page = request.form.get("next_page")

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT pin FROM auth WHERE id=1").fetchone()
    conn.close()

    if row and row[0] == pin:
        session["create_auth"] = True
        return redirect(next_page)

    return "Wrong PIN"


# ---------- SAVE PROJECT ----------
@app.route("/save", methods=["POST"])
def save():

    if not session.get("create_auth"):
        return redirect("/create")

    name = request.form.get("name")
    ptype = request.form.get("type")
    file = request.files.get("file")

    if not file or file.filename == "":
        return "No file uploaded"

    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO projects(name,file,type) VALUES(?,?,?)",
        (name, filename, ptype)
    )
    conn.commit()
    conn.close()

    return redirect("/")


# ---------- DELETE PROJECT ----------
@app.route("/delete/<int:id>")
def delete_project(id):

    if not session.get("create_auth"):
        return redirect("/create")

    conn = sqlite3.connect(DB_PATH)

    project = conn.execute(
        "SELECT file FROM projects WHERE id=?",
        (id,)
    ).fetchone()

    if project:
        filepath = os.path.join(UPLOAD_FOLDER, project[0])
        if os.path.exists(filepath):
            os.remove(filepath)

    conn.execute("DELETE FROM projects WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------- WALL AR ----------
@app.route("/wall-ar")
def wall_ar():
    return render_template("wall_ar.html")


# ---------- SERVE UPLOAD FILES ----------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(path):
        abort(404)

    return send_from_directory(UPLOAD_FOLDER, filename)


# ---------- LOCAL RUN ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)