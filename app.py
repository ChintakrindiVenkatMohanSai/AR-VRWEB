import os
from flask import Flask, render_template, request, redirect, session, abort
from flask_sqlalchemy import SQLAlchemy
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Load .env locally only
load_dotenv()

app = Flask(__name__)

# ---------- SECRET KEY ----------
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# ---------- SESSION FIX FOR MOBILE HTTPS ----------
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"

# ---------- DATABASE ----------
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    db_url = "sqlite:///local.db"

# Fix postgres:// issue (Railway/Render)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True
}

db = SQLAlchemy(app)

# ---------- CLOUDINARY ----------
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)

# ---------- MODEL ----------
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_public_id = db.Column(db.String(200))
    type = db.Column(db.String(50), nullable=False)


with app.app_context():
    db.create_all()


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


@app.route("/create")
def create_project():
    if not session.get("create_auth"):
        return render_template("pin_login.html", next_page="/create")
    return render_template("create_project.html")


@app.route("/verify-pin", methods=["POST"])
def verify_pin():
    pin = request.form.get("pin")
    next_page = request.form.get("next_page", "/")

    correct_pin = os.environ.get("ADMIN_PIN", "1234")

    if pin == correct_pin:
        session["create_auth"] = True
        session.permanent = True
        return redirect(next_page)

    return render_template("pin_login.html", error="Wrong PIN")


@app.route("/save", methods=["POST"])
def save():
    if not session.get("create_auth"):
        return redirect("/create")

    name = request.form.get("name")
    ptype = request.form.get("type")
    file = request.files.get("file")

    if not file:
        return "No file selected", 400

    try:
        resource_type = "image" if ptype == "image" else "raw"

        upload_result = cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            folder="ar-projects"
        )

        project = Project(
            name=name,
            file_url=upload_result["secure_url"],
            file_public_id=upload_result.get("public_id"),
            type=ptype
        )

        db.session.add(project)
        db.session.commit()

        return redirect("/")

    except Exception as e:
        db.session.rollback()
        return f"Upload error: {e}", 500


@app.route("/delete/<int:id>")
def delete_project(id):
    if not session.get("create_auth"):
        return redirect("/create")

    project = Project.query.get_or_404(id)

    try:
        if project.file_public_id:
            cloudinary.uploader.destroy(project.file_public_id)

        db.session.delete(project)
        db.session.commit()

    except:
        db.session.rollback()
        return "Delete failed", 500

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/wall-ar")
def wall_ar():
    return render_template("wall_ar.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)