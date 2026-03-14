import os
from flask import Flask, render_template, request, redirect, session, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ---------- LOAD ENV ----------
load_dotenv()

app = Flask(__name__)

# ---------- SECRET KEY ----------
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# ---------- SESSION FIX ----------
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"

# ---------- DATABASE ----------
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    db_url = "sqlite:///local.db"

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- UPLOAD CONFIG ----------

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "glb"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------- DATABASE MODEL ----------

class Project(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)

    file_url = db.Column(db.String(500), nullable=False)

    type = db.Column(db.String(50), nullable=False)


with app.app_context():
    db.create_all()

# ---------- SERVE UPLOADED FILES ----------


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ---------- ROUTES ----------


@app.route("/")
def dashboard():

    projects = Project.query.all()

    return render_template("dashboard.html", projects=projects)


@app.route("/image-ar/<int:project_id>")
def image_ar(project_id):

    project = Project.query.get_or_404(project_id)

    if project.type != "image":
        abort(404)

    return render_template("image_ar.html", project=project)


@app.route("/model-ar/<int:project_id>")
def model_ar(project_id):

    project = Project.query.get_or_404(project_id)

    if project.type != "model":
        abort(404)

    return render_template("model_ar.html", project=project)


# ---------- CREATE PROJECT ----------


@app.route("/create")
def create_project():

    if not session.get("create_auth"):

        return render_template(
            "pin_login.html",
            next_page="/create"
        )

    return render_template("create_project.html")


# ---------- VERIFY PIN ----------


@app.route("/verify-pin", methods=["POST"])
def verify_pin():

    pin = request.form.get("pin")

    next_page = request.form.get("next_page") or "/"

    correct_pin = os.environ.get("ADMIN_PIN", "1234")

    if pin == correct_pin:

        session["create_auth"] = True

        session.permanent = True

        return redirect(next_page)

    return render_template(
        "pin_login.html",
        error="Wrong PIN",
        next_page=next_page
    )


# ---------- SAVE PROJECT ----------


@app.route("/save", methods=["POST"])
def save():

    if not session.get("create_auth"):
        return redirect("/create")

    name = request.form.get("name")

    ptype = request.form.get("type")

    file = request.files.get("file")

    if not file or file.filename == "":
        return "No file selected", 400

    if not allowed_file(file.filename):
        return "File type not allowed", 400

    try:

        filename = secure_filename(file.filename)

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(filepath)

        file_url = f"/uploads/{filename}"

        project = Project(
            name=name,
            file_url=file_url,
            type=ptype
        )

        db.session.add(project)

        db.session.commit()

        return redirect("/")

    except Exception as e:

        db.session.rollback()

        return f"Upload error: {e}", 500


# ---------- DELETE PROJECT ----------


@app.route("/delete/<int:id>")
def delete_project(id):

    if not session.get("create_auth"):
        return redirect("/create")

    project = Project.query.get_or_404(id)

    try:

        if project.file_url.startswith("/uploads/"):

            filename = project.file_url.split("/")[-1]

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            if os.path.exists(filepath):
                os.remove(filepath)

        db.session.delete(project)

        db.session.commit()

    except:

        db.session.rollback()

        return "Delete failed", 500

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


# ---------- RUN SERVER ----------


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
