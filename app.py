from flask import Flask, render_template, request, redirect, send_from_directory, abort, session
import sqlite3, os, random, smtplib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"   # session security

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

        # NEW AUTH TABLE
        conn.execute("""
        CREATE TABLE IF NOT EXISTS auth(
            id INTEGER PRIMARY KEY,
            pin TEXT,
            email TEXT
        )
        """)

init_db()


# ---------- DASHBOARD ----------
@app.route("/")
def dashboard():
    with sqlite3.connect("projects.db") as conn:
        projects = conn.execute("SELECT * FROM projects").fetchall()
    return render_template("dashboard.html", projects=projects)


# ---------- PIN LOGIN ----------
@app.route("/login")
def login():
    return render_template("pin_login.html")


@app.route("/verify-pin", methods=["POST"])
def verify_pin():
    pin = request.form["pin"]

    with sqlite3.connect("projects.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT pin FROM auth WHERE id=1")
        row = cur.fetchone()

    if row and row[0] == pin:
        session["auth"] = True
        return redirect("/create")

    return "Wrong PIN"


# ---------- PROTECT CREATE PAGE ----------
@app.route("/create")
def create_project():
    if not session.get("auth"):
        return redirect("/login")
    return render_template("create_project.html")


# ---------- SAVE PROJECT ----------
@app.route("/save", methods=["POST"])
def save():
    name = request.form.get("name")
    ptype = request.form.get("type")
    file = request.files.get("file")

    if not file or file.filename == "":
        return "No file uploaded"

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    with sqlite3.connect("projects.db") as conn:
        conn.execute(
            "INSERT INTO projects(name,file,type) VALUES(?,?,?)",
            (name, filename, ptype)
        )
        conn.commit()

    return redirect("/")


# ---------- FORGOT PIN ----------
@app.route("/forgot")
def forgot():
    return render_template("forgot_pin.html")


@app.route("/send-otp", methods=["POST"])
def send_otp():
    email = request.form["email"]
    otp = str(random.randint(1000, 9999))

    session["otp"] = otp
    session["email"] = email

    # Gmail SMTP (use app password)
    sender = "mohansaichintakrindi.009@gmail.com"
    password = "sytitkrbenmlkqzr"

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, email, f"Your OTP: {otp}")
        server.quit()
    except:
        return "Email sending failed"

    return redirect("/reset-pin")


@app.route("/reset-pin")
def reset_pin():
    return render_template("reset_pin.html")


@app.route("/save-pin", methods=["POST"])
def save_pin():
    otp = request.form["otp"]
    newpin = request.form["pin"]

    if otp != session.get("otp"):
        return "Invalid OTP"

    with sqlite3.connect("projects.db") as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auth(id,pin,email) VALUES(1,?,?)",
            (newpin, session["email"])
        )
        conn.commit()

    return redirect("/login")


# ---------- AR ROUTES ----------
@app.route("/image-ar/<path:file>")
def image_ar(file):
    return render_template("image_ar.html", file=file)


@app.route("/model-ar/<path:file>")
def model_ar(file):
    return render_template("model_ar.html", file=file)


@app.route("/wall-ar")
def wall_ar():
    return render_template("wall_ar.html")


# ---------- SERVE FILES ----------
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, filename)


# ---------- DELETE PROJECT ----------
@app.route("/delete/<int:id>")
def delete_project(id):

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


# ---------- RUN SERVER ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)