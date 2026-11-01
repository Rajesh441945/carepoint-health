import os, sqlite3
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "healthcare.db"))

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK(role IN ('patient','doctor','admin')),
      phone TEXT DEFAULT '', specialization TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS appointments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER NOT NULL REFERENCES users(id),
      doctor_id INTEGER NOT NULL REFERENCES users(id),
      appointment_date TEXT NOT NULL, appointment_time TEXT NOT NULL,
      reason TEXT DEFAULT '',
      status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending','Confirmed','Completed','Cancelled')),
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS medical_reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER NOT NULL REFERENCES users(id),
      doctor_id INTEGER NOT NULL REFERENCES users(id),
      report_date TEXT NOT NULL, title TEXT NOT NULL, notes TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    seeds = [
      ("System Administrator","admin@healthcare.local","Admin@123","admin","",""),
      ("Dr. Rahul Sharma","rahul@healthcare.local","Doctor@123","doctor","9876500001","General Physician"),
      ("Dr. Priya Patil","priya@healthcare.local","Doctor@123","doctor","9876500002","Cardiologist"),
      ("Dr. Amit Deshmukh","amit@healthcare.local","Doctor@123","doctor","9876500003","Orthopedic Specialist")
    ]
    for name,email,pw,role,phone,spec in seeds:
        conn.execute("INSERT OR IGNORE INTO users(name,email,password_hash,role,phone,specialization) VALUES(?,?,?,?,?,?)",
                     (name,email,generate_password_hash(pw),role,phone,spec))
    conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_user():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

@app.route("/")
def home():
    doctors = db().execute("SELECT id,name,specialization FROM users WHERE role='doctor' ORDER BY name").fetchall()
    return render_template("index.html", doctors=doctors, today=date.today().isoformat())

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        phone=request.form.get("phone","").strip()
        password=request.form.get("password","")
        if not name or not email or len(password)<8:
            flash("Enter your name and email. Password must contain at least 8 characters.", "danger")
        else:
            try:
                db().execute("INSERT INTO users(name,email,password_hash,role,phone) VALUES(?,?,?,'patient',?)",
                             (name,email,generate_password_hash(password),phone))
                db().commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email address is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        user=db().execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session.update(user_id=user["id"],name=user["name"],role=user["role"])
            flash("Welcome back, " + user["name"] + "!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    role=session["role"]; uid=session["user_id"]
    if role=="admin":
        stats={
          "patients":db().execute("SELECT COUNT(*) n FROM users WHERE role='patient'").fetchone()["n"],
          "doctors":db().execute("SELECT COUNT(*) n FROM users WHERE role='doctor'").fetchone()["n"],
          "appointments":db().execute("SELECT COUNT(*) n FROM appointments").fetchone()["n"],
          "pending":db().execute("SELECT COUNT(*) n FROM appointments WHERE status='Pending'").fetchone()["n"]
        }
        appointments=db().execute("""SELECT a.*,p.name patient_name,d.name doctor_name
          FROM appointments a JOIN users p ON p.id=a.patient_id JOIN users d ON d.id=a.doctor_id
          ORDER BY a.appointment_date DESC,a.appointment_time DESC""").fetchall()
        return render_template("admin_dashboard.html",stats=stats,appointments=appointments)
    if role=="doctor":
        appointments=db().execute("""SELECT a.*,p.name patient_name,p.phone patient_phone
          FROM appointments a JOIN users p ON p.id=a.patient_id WHERE a.doctor_id=?
          ORDER BY a.appointment_date,a.appointment_time""",(uid,)).fetchall()
        return render_template("doctor_dashboard.html",appointments=appointments)
    appointments=db().execute("""SELECT a.*,d.name doctor_name,d.specialization
      FROM appointments a JOIN users d ON d.id=a.doctor_id WHERE a.patient_id=?
      ORDER BY a.appointment_date DESC,a.appointment_time DESC""",(uid,)).fetchall()
    reports=db().execute("""SELECT r.*,d.name doctor_name FROM medical_reports r
      JOIN users d ON d.id=r.doctor_id WHERE r.patient_id=? ORDER BY r.report_date DESC""",(uid,)).fetchall()
    doctors=db().execute("SELECT id,name,specialization FROM users WHERE role='doctor' ORDER BY name").fetchall()
    return render_template("patient_dashboard.html",appointments=appointments,reports=reports,doctors=doctors,today=date.today().isoformat())

@app.route("/appointments/book", methods=["POST"])
@roles_required("patient")
def book_appointment():
    doctor_id=request.form.get("doctor_id",type=int)
    appt_date=request.form.get("appointment_date","")
    appt_time=request.form.get("appointment_time","")
    reason=request.form.get("reason","").strip()
    doctor=db().execute("SELECT id FROM users WHERE id=? AND role='doctor'",(doctor_id,)).fetchone()
    if not doctor or not appt_date or not appt_time or appt_date < date.today().isoformat():
        flash("Please select a valid doctor, future date and time.", "danger")
    else:
        conflict=db().execute("""SELECT id FROM appointments WHERE doctor_id=? AND appointment_date=?
          AND appointment_time=? AND status IN ('Pending','Confirmed')""",(doctor_id,appt_date,appt_time)).fetchone()
        if conflict:
            flash("That doctor already has an appointment at this time. Please choose another slot.", "warning")
        else:
            db().execute("INSERT INTO appointments(patient_id,doctor_id,appointment_date,appointment_time,reason) VALUES(?,?,?,?,?)",
                         (session["user_id"],doctor_id,appt_date,appt_time,reason))
            db().commit()
            flash("Appointment request submitted. Check its status on your dashboard.", "success")
    return redirect(url_for("dashboard"))

@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@roles_required("admin","doctor")
def update_appointment(appointment_id):
    status=request.form.get("status")
    allowed={"Pending","Confirmed","Completed","Cancelled"}
    row=db().execute("SELECT * FROM appointments WHERE id=?",(appointment_id,)).fetchone()
    if status not in allowed or not row or (session["role"]=="doctor" and row["doctor_id"]!=session["user_id"]):
        flash("Unable to update this appointment.", "danger")
    else:
        db().execute("UPDATE appointments SET status=? WHERE id=?",(status,appointment_id))
        db().commit()
        flash("Appointment status updated.", "success")
    return redirect(url_for("dashboard"))

@app.route("/reports/new", methods=["GET","POST"])
@roles_required("doctor","admin")
def new_report():
    if request.method=="POST":
        patient_id=request.form.get("patient_id",type=int)
        title=request.form.get("title","").strip()
        notes=request.form.get("notes","").strip()
        report_date=request.form.get("report_date","")
        patient=db().execute("SELECT id FROM users WHERE id=? AND role='patient'",(patient_id,)).fetchone()
        if patient and title and notes and report_date:
            db().execute("INSERT INTO medical_reports(patient_id,doctor_id,report_date,title,notes) VALUES(?,?,?,?,?)",
                         (patient_id,session["user_id"],report_date,title,notes))
            db().commit()
            flash("Medical report saved.", "success")
            return redirect(url_for("dashboard"))
        flash("Please complete all report fields and select a valid patient.", "danger")
    patients=db().execute("SELECT id,name,email FROM users WHERE role='patient' ORDER BY name").fetchall()
    return render_template("new_report.html",patients=patients,today=date.today().isoformat())

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    user=db().execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
    if request.method=="POST":
        name=request.form.get("name","").strip()
        phone=request.form.get("phone","").strip()
        if name:
            db().execute("UPDATE users SET name=?,phone=? WHERE id=?",(name,phone,session["user_id"]))
            db().commit()
            session["name"]=name
            flash("Profile updated.", "success")
            return redirect(url_for("profile"))
        flash("Name cannot be empty.", "danger")
    return render_template("profile.html",user=user)

@app.errorhandler(404)
def not_found(error):
    return render_template("message.html",title="Page not found",message="The page you requested does not exist."),404

init_db()

if __name__=="__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG","0")=="1", host="127.0.0.1", port=int(os.environ.get("PORT",5000)))
