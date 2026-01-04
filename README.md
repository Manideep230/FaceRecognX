# FaceRecognX

# FaceRecognX – Web-based Face Recognition Attendance System

A full-stack **face recognition attendance system** built with **Python, Flask, OpenCV, face_recognition, and MongoDB**.  
Admin can manage teachers, teachers can register students with multi-angle face samples, and mark attendance using webcam from a web interface only (no ESP32 required).

---

## Features

- **Admin module**
  - Secure admin login (`admin` user auto-created on first run)
  - Register new teachers (ID, Name, Email, Password)
  - View all registered teachers and students in tables

- **Teacher module**
  - Login with teacher ID & password
  - Register students with:
    - Student ID, Name, Section
    - Automatic face capture (face-only crops, multiple angles)
  - Live webcam **attendance capture** page
    - Recognizes students using stored encodings
    - Marks attendance only once per day per student
    - Shows feedback:
      - New attendance
      - Already marked today
  - **Daily attendance page**
    - Select date
    - View all students present with: ID, Name, Section, Time, Date

- **Face registration**
  - Captures many frames (e.g., 240 frames) in a short time window
  - Uses **TensorFlow.js BlazeFace** in the browser to detect and crop only the face region (no background)
  - Sends cropped face images to backend, where **face_recognition** generates encodings and stores them in MongoDB

- **Face recognition & attendance**
  - Uses `face_recognition` (dlib) encodings stored in MongoDB
  - On each webcam frame:
    - Detect faces
    - Compute encodings
    - Compare with database using Euclidean distance
  - Threshold tuned to reduce false positives
  - Attendance document includes `student_id`, `name`, `date`, `time`, `full_timestamp`, `marked_by`

---

## Tech Stack

- **Backend**
  - Python 3
  - Flask (web framework)
  - Jinja2 (HTML templating)
  - PyMongo (MongoDB driver)
  - bcrypt / Flask-Bcrypt (password hashing)
  - OpenCV (`cv2`) for frame processing
  - `face_recognition` for face encodings & matching
  - NumPy

- **Database**
  - MongoDB Atlas or local MongoDB instance
  - Collections:
    - `teachers`
    - `students`
    - `web_attendance`

- **Frontend**
  - HTML5, CSS3
  - Bootstrap 5
  - Vanilla JavaScript (Fetch API)
  - TensorFlow.js + BlazeFace (client-side face detection & cropping in registration page)[web:13][web:16][web:22]

---

## Project Structure

```text
FaceRecognX/
├── app.py                 # Flask application (routes, logic)
├── mongo_config.py        # MongoDB connection & collections
├── requirements.txt       # Python dependencies
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── teacher_login.html
│   ├── admin_register.html
│   ├── admin_dashboard.html
│   ├── teacher_dashboard.html
│   ├── register_student.html
│   ├── capture_attendance.html
│   └── daily_attendance.html
└── static/                # (optional) custom CSS/JS/assets
