from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_bcrypt import Bcrypt
import cv2
import face_recognition
import numpy as np
import base64
from datetime import datetime
import json
from mongo_config import (
    teachers_collection,
    students_collection,
    web_attendance_collection,
)

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
bcrypt = Bcrypt(app)

# ========== ADMIN DEFAULT CREDENTIALS ==========
ADMIN_ID = "admin"
ADMIN_PASSWORD_HASH = bcrypt.generate_password_hash("admin").decode("utf-8")

# Create admin user if doesn't exist (runs only once)
if not teachers_collection.find_one({"teacher_id": ADMIN_ID}):
    teachers_collection.insert_one({
        "teacher_id": ADMIN_ID,
        "name": "Admin",
        "email": "admin@facerecognx.com",
        "password": ADMIN_PASSWORD_HASH,
        "role": "admin"
    })

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        return teacher_login()
    return render_template("teacher_login.html")

# ---------- ADMIN ----------
@app.route("/admin/register_teacher", methods=["GET", "POST"])
def register_teacher():
    if "teacher_id" not in session or session["teacher_id"] != ADMIN_ID:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        teacher_id = request.form["teacher_id"].strip()
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        if teachers_collection.find_one({"teacher_id": teacher_id}):
            flash("Teacher ID already exists!", "danger")
            return redirect(url_for("register_teacher"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        teachers_collection.insert_one({
            "teacher_id": teacher_id,
            "name": name,
            "email": email,
            "password": hashed_pw,
            "role": "teacher"
        })

        flash("Teacher registered successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_register.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if "teacher_id" not in session or session["teacher_id"] != ADMIN_ID:
        return redirect(url_for("index"))
    
    teachers = list(teachers_collection.find({"role": "teacher"}, {"password": 0}))
    students = list(students_collection.find({}, {"encodings": 0}))
    return render_template("admin_dashboard.html", teachers=teachers, students=students)

# ---------- TEACHER AUTH ----------
@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        teacher_id = request.form["teacher_id"].strip()
        password = request.form["password"].strip()

        teacher = teachers_collection.find_one({"teacher_id": teacher_id})
        if teacher and bcrypt.check_password_hash(teacher["password"], password):
            session["teacher_id"] = teacher["teacher_id"]
            session["teacher_name"] = teacher["name"]
            session["is_admin"] = (teacher_id == ADMIN_ID)
            
            if teacher_id == ADMIN_ID:
                flash("Login successful!", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Login successful!", "success")
                return redirect(url_for("teacher_dashboard"))
        else:
            flash("❌ Invalid credentials!", "danger")

    return render_template("teacher_login.html")

@app.route("/teacher/dashboard")
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("index"))
    
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))
    
    return render_template("teacher_dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------- STUDENT REGISTRATION ----------
@app.route("/teacher/register_student", methods=["GET", "POST"])
def register_student():
    if "teacher_id" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        data = request.get_json()
        student_id = data.get("student_id", "").strip()
        name = data.get("name", "").strip()
        section = data.get("section", "").strip()
        images = data.get("images", [])

        if not student_id or not name or not section:
            return jsonify({"ok": False, "msg": "All fields required"}), 400

        if students_collection.find_one({"student_id": student_id}):
            return jsonify({"ok": False, "msg": "Student ID already exists"}), 400

        encodings = []
        for img_b64 in images:
            try:
                header, encoded = img_b64.split(",", 1)
                img_data = base64.b64decode(encoded)
                npimg = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = face_recognition.face_locations(rgb)
                if len(faces) == 1:
                    enc = face_recognition.face_encodings(rgb, faces)[0]
                    encodings.append(enc.tolist())
            except:
                continue

        MIN_VALID_ENCS = 25
        if len(encodings) < MIN_VALID_ENCS:
            return jsonify({
                "ok": False,
                "msg": f"Got {len(encodings)} valid encodings from {len(images)} face crops. Need {MIN_VALID_ENCS}."
            }), 400

        students_collection.insert_one({
            "student_id": student_id,
            "name": name,
            "section": section,
            "encodings": encodings,
            "registered_by": session["teacher_id"],
            "registered_on": datetime.now()
        })

        return jsonify({"ok": True, "msg": "Student registered successfully"})

    return render_template("register_student.html")

# ---------- ATTENDANCE CAPTURE ----------
@app.route("/teacher/capture_attendance")
def capture_attendance():
    if "teacher_id" not in session:
        return redirect(url_for("index"))
    return render_template("capture_attendance.html")

# ---------- DAILY ATTENDANCE ----------
@app.route("/teacher/daily_attendance")
def daily_attendance():
    if "teacher_id" not in session:
        return redirect(url_for("index"))
    
    selected_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    attendance_records = list(web_attendance_collection.find({
        "date": selected_date
    }).sort("full_timestamp"))
    
    students = list(students_collection.find({}, {
        "student_id": 1, 
        "name": 1, 
        "section": 1
    }))
    student_dict = {s["student_id"]: s for s in students}
    
    attendance_with_section = []
    for record in attendance_records:
        student_id = record["student_id"]
        record["section"] = student_dict.get(student_id, {}).get("section", "N/A")
        attendance_with_section.append(record)
    
    return render_template("daily_attendance.html", 
                         attendance=attendance_with_section,
                         selected_date=selected_date)

# ---------- API ROUTES ----------
@app.route("/api/mark_attendance", methods=["POST"])
def api_mark_attendance():
    if "teacher_id" not in session:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401

    data = request.get_json()
    frame_b64 = data.get("frame")

    try:
        header, encoded = frame_b64.split(",", 1)
        img_data = base64.b64decode(encoded)
        npimg = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        students = list(students_collection.find({}, {"encodings": 1, "name": 1, "student_id": 1}))
        known_encodings = []
        known_names = []
        known_ids = []

        for s in students:
            for enc in s["encodings"]:
                known_encodings.append(np.array(enc))
                known_names.append(s["name"])
                known_ids.append(s["student_id"])

        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        marked = []
        already_marked = []

        today = datetime.now().strftime("%Y-%m-%d")

        for encoding in encodings:
            if len(known_encodings) == 0:
                continue
            distances = face_recognition.face_distance(known_encodings, encoding)
            if len(distances) == 0:
                continue
            min_dist = np.min(distances)
            idx = np.argmin(distances)

            if min_dist < 0.48:
                student_id = known_ids[idx]
                name = known_names[idx]

                exists = web_attendance_collection.find_one({
                    "student_id": student_id,
                    "date": today
                })
                if not exists:
                    web_attendance_collection.insert_one({
                        "student_id": student_id,
                        "name": name,
                        "date": today,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "full_timestamp": datetime.now(),
                        "marked_by": session["teacher_id"]
                    })
                    marked.append({"student_id": student_id, "name": name})
                else:
                    already_marked.append({"student_id": student_id, "name": name})

        return jsonify({
            "ok": True, 
            "marked": marked,
            "already_marked": already_marked
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
