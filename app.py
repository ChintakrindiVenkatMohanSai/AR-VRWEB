from flask import Flask, render_template, request, redirect, send_from_directory, abort, session
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- DATABASE ----------
def init_db():
    with sqlite3.connect("projects.db") as conn:

        conn.execute("""
        CREATE TABLE IF NOT EXISTS projects(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            file TEXT,
            type TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS auth(
            id INTEGER PRIMARY KEY,
            pin TEXT,
            email TEXT
        )
        """)

        conn.execute("""
        INSERT OR IGNORE INTO auth(id,pin,email)
        VALUES(1,'1234','admin@email.com')
        """)

        conn.commit()

init_db()


# ---------- DASHBOARD ----------
@app.route("/")
def dashboard():
    with sqlite3.connect("projects.db") as conn:
        projects = conn.execute("SELECT * FROM projects").fetchall()
    return render_template("dashboard.html", projects=projects)


# ---------- CREATE PROJECT WITH PIN ----------
@app.route("/create")
def create_project():

    # If PIN not verified -> show PIN page first
    if not session.get("create_auth"):
        return render_template("pin_login.html", next_page="/create")

    # After PIN success -> upload page
    return render_template("create_project.html")


# ---------- VERIFY PIN ----------
@app.route("/verify-pin", methods=["POST"])
def verify_pin():

    pin = request.form.get("pin")
    next_page = request.form.get("next_page")

    with sqlite3.connect("projects.db") as conn:
        row = conn.execute("SELECT pin FROM auth WHERE id=1").fetchone()

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

    with sqlite3.connect("projects.db") as conn:
        conn.execute(
            "INSERT INTO projects(name,file,type) VALUES(?,?,?)",
            (name, filename, ptype)
        )
        conn.commit()

    return redirect("/")


# ---------- DELETE ----------
@app.route("/delete/<int:id>")
def delete_project(id):

    if not session.get("create_auth"):
        return redirect("/create")

    with sqlite3.connect("projects.db") as conn:
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

    return redirect("/")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("create_auth", None)
    return redirect("/")


# ---------- WALL AR ----------
@app.route("/wall-ar")
def wall_ar():
    return render_template("wall_ar.html")


# ---------- SERVE UPLOADS ----------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(path):
        abort(404)

    return send_from_directory(UPLOAD_FOLDER, filename)


# ---------- RUN ----------
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)