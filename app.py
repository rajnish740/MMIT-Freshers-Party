from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

# Session ke liye secret key
app.secret_key = "mmit-freshers-2026-secret-key"

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==============================
# DATABASE CREATE / UPDATE
# ==============================

def create_database():

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            roll_number TEXT NOT NULL,

            semester TEXT NOT NULL,

            branch TEXT NOT NULL,

            mobile TEXT NOT NULL,

            email TEXT,

            gender TEXT NOT NULL,

            payment_status TEXT DEFAULT 'PENDING',

            utr TEXT,

            payment_screenshot TEXT

        )
    """)

    cursor.execute("PRAGMA table_info(students)")

    columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    if "utr" not in columns:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN utr TEXT
        """)

    if "payment_screenshot" not in columns:

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN payment_screenshot TEXT
        """)

    conn.commit()
    conn.close()


# ==============================
# HOME
# ==============================

@app.route("/")
def home():

    return render_template("index.html")


# ==============================
# REGISTRATION
# ==============================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        roll_number = request.form["roll_number"]
        semester = request.form["semester"]
        branch = request.form["branch"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        gender = request.form["gender"]

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO students
            (
                name,
                roll_number,
                semester,
                branch,
                mobile,
                email,
                gender,
                payment_status
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        """, (
            name,
            roll_number,
            semester,
            branch,
            mobile,
            email,
            gender,
            "PENDING"
        ))

        conn.commit()

        registration_id = cursor.lastrowid

        conn.close()

        return render_template(
            "payment.html",
            registration_no=registration_id,
            student_name=name
        )

    return render_template("register.html")


# ==============================
# PAYMENT CONFIRMATION PAGE
# ==============================

@app.route("/payment-submit/<int:student_id>")
def payment_submit_page(student_id):

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name

        FROM students

        WHERE id = ?

    """, (student_id,))

    student = cursor.fetchone()

    conn.close()

    if student is None:

        return "Student registration not found."

    return render_template(
        "payment_submit.html",

        registration_id=student[0],

        student_id=student[0],

        student_name=student[1]
    )


# ==============================
# SAVE PAYMENT DETAILS
# ==============================

@app.route("/payment-submit", methods=["POST"])
def save_payment():

    student_id = request.form["student_id"]

    utr = request.form["utr"].strip()

    screenshot = request.files.get(
        "payment_screenshot"
    )

    if not utr:

        return "UTR / Transaction ID is required."

    if screenshot is None or screenshot.filename == "":

        return "Payment screenshot is required."

    filename = secure_filename(
        screenshot.filename
    )

    filename = f"{student_id}_{filename}"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    screenshot.save(filepath)

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students

        SET
            payment_status = ?,
            utr = ?,
            payment_screenshot = ?

        WHERE id = ?

    """, (
        "SUBMITTED",
        utr,
        filename,
        student_id
    ))

    conn.commit()
    conn.close()

    return """

    <div style="
        font-family: Arial;
        text-align: center;
        padding: 50px;
    ">

        <h1>
            🎉 Payment Details Submitted!
        </h1>

        <p>
            आपका payment record successfully submit हो गया है।
        </p>

        <p>
            Admin payment verify करेगा।
        </p>

        <br>

        <a href="/">
            ← Back to Home
        </a>

    </div>

    """


# ==============================
# STUDENT PAYMENT STATUS
# ==============================

@app.route("/payment-status", methods=["GET", "POST"])
def payment_status():

    if request.method == "POST":

        registration_id = request.form[
            "registration_id"
        ].strip()

        mobile = request.form[
            "mobile"
        ].strip()

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                roll_number,
                semester,
                branch,
                mobile,
                utr,
                payment_status

            FROM students

            WHERE id = ?

            AND mobile = ?

        """, (
            registration_id,
            mobile
        ))

        student = cursor.fetchone()

        conn.close()

        if student is None:

            return render_template(
                "student_status.html",
                error="❌ Registration ID या Mobile Number गलत है।"
            )

        return render_template(
            "student_status.html",
            student=student
        )

    return render_template(
        "student_status.html"
    )


# ==============================
# ADMIN LOGIN PAGE
# ==============================

@app.route("/admin")
def admin_login_page():

    return render_template(
        "admin_login.html"
    )


# ==============================
# ADMIN LOGIN
# ==============================

@app.route("/admin-login", methods=["POST"])
def admin_login():

    username = request.form["username"]

    password = request.form["password"]

    if username == "admin" and password == "admin123":

        session["admin_logged_in"] = True

        return redirect(
            "/admin/dashboard"
        )

    return """

    <div style="
        font-family: Arial;
        text-align: center;
        padding: 50px;
    ">

        <h2>
            ❌ Invalid Username or Password
        </h2>

        <a href="/admin">
            ← Try Again
        </a>

    </div>

    """


# ==============================
# ADMIN DASHBOARD
# ==============================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin_logged_in"):

        return redirect("/admin")

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            roll_number,
            semester,
            branch,
            mobile,
            utr,
            payment_status,
            payment_screenshot

        FROM students

        ORDER BY id DESC

    """)

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        students=students
    )


# ==============================
# VERIFY PAYMENT
# ==============================

@app.route(
    "/admin/verify/<int:student_id>",
    methods=["POST"]
)
def verify_payment(student_id):

    if not session.get("admin_logged_in"):

        return redirect("/admin")

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students

        SET payment_status = ?

        WHERE id = ?

    """, (
        "VERIFIED",
        student_id
    ))

    conn.commit()
    conn.close()

    return redirect(
        "/admin/dashboard"
    )


# ==============================
# REJECT PAYMENT
# ==============================

@app.route(
    "/admin/reject/<int:student_id>",
    methods=["POST"]
)
def reject_payment(student_id):

    if not session.get("admin_logged_in"):

        return redirect("/admin")

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students

        SET payment_status = ?

        WHERE id = ?

    """, (
        "REJECTED",
        student_id
    ))

    conn.commit()
    conn.close()

    return redirect(
        "/admin/dashboard"
    )


# ==============================
# ADMIN PAYMENT RECEIPT
# ==============================

@app.route(
    "/admin/receipt/<int:student_id>"
)
def payment_receipt(student_id):

    if not session.get("admin_logged_in"):

        return redirect("/admin")

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            roll_number,
            semester,
            branch,
            mobile,
            utr,
            payment_status

        FROM students

        WHERE id = ?

    """, (student_id,))

    student = cursor.fetchone()

    conn.close()

    if student is None:

        return "Student not found."

    if student[7] != "VERIFIED":

        return """

        <div style="
            font-family: Arial;
            text-align: center;
            padding: 50px;
        ">

            <h2>
                ⚠️ Payment Not Verified
            </h2>

            <p>
                Receipt केवल verified payment के बाद
                generate की जा सकती है।
            </p>

            <br>

            <a href="/admin/dashboard">
                ← Back to Dashboard
            </a>

        </div>

        """

    return render_template(
        "receipt.html",
        student=student
    )


# ==============================
# STUDENT RECEIPT
# ==============================

@app.route(
    "/student/receipt/<int:student_id>"
)
def student_receipt(student_id):

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            roll_number,
            semester,
            branch,
            mobile,
            utr,
            payment_status

        FROM students

        WHERE id = ?

    """, (student_id,))

    student = cursor.fetchone()

    conn.close()

    if student is None:

        return "Student not found."

    # Receipt केवल VERIFIED payment के लिए

    if student[7] != "VERIFIED":

        return """

        <div style="
            font-family: Arial;
            text-align: center;
            padding: 50px;
        ">

            <h2>
                ⚠️ Payment Not Verified
            </h2>

            <p>
                Receipt केवल verified payment के बाद
                generate की जा सकती है।
            </p>

            <br>

            <a href="/payment-status">
                ← Back to Payment Status
            </a>

        </div>

        """

    return render_template(
        "receipt.html",
        student=student
    )


# ==============================
# ADMIN LOGOUT
# ==============================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect("/admin")


# ==============================
# START SERVER
# ==============================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)