from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
from decimal import Decimal, InvalidOperation
from werkzeug.utils import secure_filename


app = Flask(__name__)


# ==================================================
# SECRET KEY
# ==================================================

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)


# ==================================================
# UPLOAD FOLDER
# ==================================================

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==================================================
# DATABASE CONNECTION
# ==================================================

def get_db_connection():

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    return psycopg2.connect(
        database_url,
        sslmode="require"
    )


# ==================================================
# CREATE / UPDATE DATABASE
# ==================================================

def create_database():

    conn = get_db_connection()

    cursor = conn.cursor()


    # ==================================================
    # CREATE TABLE
    # ==================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (

            id SERIAL PRIMARY KEY,

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


    # ==================================================
    # NEW COLUMNS
    # ==================================================

    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS participant_type TEXT
    """)


    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS payment_amount NUMERIC(10,2)
    """)


    conn.commit()

    cursor.close()

    conn.close()


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

try:

    create_database()

except Exception as e:

    print(
        "Database initialization error:",
        e
    )


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==================================================
# REGISTRATION
# ==================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form[
            "name"
        ].strip()


        participant_type = request.form[
            "participant_type"
        ].strip()


        roll_number = request.form.get(
            "roll_number",
            ""
        ).strip()


        year = request.form.get(
            "year",
            ""
        ).strip()


        teacher_amount = request.form.get(
            "teacher_amount",
            ""
        ).strip()


        branch = request.form.get(
            "branch",
            ""
        ).strip()


        mobile = request.form[
            "mobile"
        ].strip()


        email = request.form.get(
            "email",
            ""
        ).strip()


        gender = request.form[
            "gender"
        ].strip()


        # ==================================================
        # AMOUNT CALCULATION
        # ==================================================

        if participant_type == "Student":

            if year not in [
                "1st Year",
                "2nd Year",
                "3rd Year"
            ]:

                return """
                <h2>❌ Please select a valid Year.</h2>
                <a href="/register">← Back</a>
                """


            if year == "1st Year":

                payment_amount = Decimal("199")

            else:

                payment_amount = Decimal("300")


        elif participant_type == "Teacher":

            if not teacher_amount:

                return """
                <h2>❌ Teacher amount is required.</h2>
                <a href="/register">← Back</a>
                """


            try:

                payment_amount = Decimal(
                    teacher_amount
                )

            except InvalidOperation:

                return """
                <h2>❌ Invalid teacher amount.</h2>
                <a href="/register">← Back</a>
                """


            if payment_amount <= 0:

                return """
                <h2>❌ Amount must be greater than 0.</h2>
                <a href="/register">← Back</a>
                """


            year = "Teacher"


        else:

            return """
            <h2>❌ Invalid participant type.</h2>
            <a href="/register">← Back</a>
            """


        # ==================================================
        # STUDENT / TEACHER VALIDATION
        # ==================================================

        if participant_type == "Student":

            if not roll_number:

                return """
                <h2>❌ Roll Number is required.</h2>
                <a href="/register">← Back</a>
                """


            if not branch:

                return """
                <h2>❌ Branch is required.</h2>
                <a href="/register">← Back</a>
                """


        else:

            roll_number = (
                roll_number
                if roll_number
                else "N/A"
            )


            branch = (
                branch
                if branch
                else "Teacher"
            )


        # ==================================================
        # DATABASE INSERT
        # ==================================================

        conn = get_db_connection()

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
                payment_status,
                participant_type,
                payment_amount
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )

            RETURNING id
        """, (

            name,

            roll_number,

            year,

            branch,

            mobile,

            email,

            gender,

            "PENDING",

            participant_type,

            payment_amount

        ))


        registration_id = cursor.fetchone()[0]


        conn.commit()

        cursor.close()

        conn.close()


        # ==================================================
        # PAYMENT PAGE
        # ==================================================

        return render_template(

            "payment.html",

            registration_no=registration_id,

            student_name=name,

            amount=payment_amount,

            participant_type=participant_type,

            year=year

        )


    return render_template(
        "register.html"
    )


# ==================================================
# PAYMENT SUBMIT PAGE
# ==================================================

@app.route(
    "/payment-submit/<int:student_id>"
)
def payment_submit_page(student_id):

    conn = get_db_connection()

    cursor = conn.cursor()


    cursor.execute("""
        SELECT
            id,
            name,
            payment_amount
        FROM students
        WHERE id = %s
    """, (
        student_id,
    ))


    student = cursor.fetchone()


    cursor.close()

    conn.close()


    if student is None:

        return "Student registration not found."


    return render_template(

        "payment_submit.html",

        registration_id=student[0],

        student_id=student[0],

        student_name=student[1],

        amount=student[2]

    )


# ==================================================
# SAVE PAYMENT DETAILS
# ==================================================

@app.route(
    "/payment-submit",
    methods=["POST"]
)
def save_payment():

    student_id = request.form[
        "student_id"
    ]


    utr = request.form[
        "utr"
    ].strip()


    screenshot = request.files.get(
        "payment_screenshot"
    )


    if not utr:

        return """
        <h2>❌ UTR / Transaction ID is required.</h2>
        <a href="javascript:history.back()">← Back</a>
        """


    if (
        screenshot is None
        or screenshot.filename == ""
    ):

        return """
        <h2>❌ Payment screenshot is required.</h2>
        <a href="javascript:history.back()">← Back</a>
        """


    filename = secure_filename(
        screenshot.filename
    )


    filename = f"{student_id}_{filename}"


    filepath = os.path.join(

        app.config[
            "UPLOAD_FOLDER"
        ],

        filename

    )


    screenshot.save(filepath)


    conn = get_db_connection()

    cursor = conn.cursor()


    cursor.execute("""
        UPDATE students

        SET

            payment_status = %s,

            utr = %s,

            payment_screenshot = %s

        WHERE id = %s

    """, (

        "SUBMITTED",

        utr,

        filename,

        student_id

    ))


    conn.commit()

    cursor.close()

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


# ==================================================
# STUDENT PAYMENT STATUS
# ==================================================
# अब Registration ID की जगह
# UTR / Transaction ID + Mobile Number से search होगा
# ==================================================

@app.route(
    "/payment-status",
    methods=["GET", "POST"]
)
def payment_status():

    if request.method == "POST":

        utr = request.form.get(
            "utr",
            ""
        ).strip()


        mobile = request.form.get(
            "mobile",
            ""
        ).strip()


        # ==================================================
        # VALIDATION
        # ==================================================

        if not utr:

            return render_template(

                "student_status.html",

                error=(
                    "❌ UTR / Transaction ID "
                    "डालना जरूरी है।"
                )

            )


        if not mobile:

            return render_template(

                "student_status.html",

                error=(
                    "❌ Mobile Number "
                    "डालना जरूरी है।"
                )

            )


        # ==================================================
        # DATABASE SEARCH
        # ==================================================

        conn = get_db_connection()

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

                participant_type,

                payment_amount

            FROM students

            WHERE utr = %s

            AND mobile = %s

        """, (

            utr,

            mobile

        ))


        student = cursor.fetchone()


        cursor.close()

        conn.close()


        # ==================================================
        # NOT FOUND
        # ==================================================

        if student is None:

            return render_template(

                "student_status.html",

                error=(
                    "❌ UTR / Transaction ID "
                    "या Mobile Number गलत है।"
                )

            )


        # ==================================================
        # SHOW PAYMENT STATUS
        # ==================================================

        return render_template(

            "student_status.html",

            student=student

        )


    return render_template(
        "student_status.html"
    )


# ==================================================
# ADMIN LOGIN PAGE
# ==================================================

@app.route("/admin")
def admin_login_page():

    return render_template(
        "admin_login.html"
    )


# ==================================================
# ADMIN LOGIN
# ==================================================

@app.route(
    "/admin-login",
    methods=["POST"]
)
def admin_login():

    username = request.form[
        "username"
    ]


    password = request.form[
        "password"
    ]


    ADMIN_USERNAME = os.environ.get(
        "ADMIN_USERNAME",
        "brijesh"
    )


    ADMIN_PASSWORD = os.environ.get(
        "ADMIN_PASSWORD",
        "Rajnish@01#200674"
    )


    if (
        username == ADMIN_USERNAME
        and
        password == ADMIN_PASSWORD
    ):

        session[
            "admin_logged_in"
        ] = True


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


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route(
    "/admin/dashboard"
)
def admin_dashboard():

    if not session.get("admin_logged_in"):
        return redirect("/admin")

    conn = get_db_connection()
    cursor = conn.cursor()

    # सभी students
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
            payment_screenshot,
            participant_type,
            payment_amount
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    # केवल VERIFIED payments की total amount
    cursor.execute("""
        SELECT COALESCE(SUM(payment_amount), 0)
        FROM students
        WHERE payment_status = 'VERIFIED'
    """)

    total_collection = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        students=students,
        total_collection=total_collection
        )


# ==================================================
# VERIFY PAYMENT
# ==================================================

@app.route(
    "/admin/verify/<int:student_id>",
    methods=["POST"]
)
def verify_payment(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            "/admin"
        )


    conn = get_db_connection()

    cursor = conn.cursor()


    cursor.execute("""
        UPDATE students

        SET payment_status = %s

        WHERE id = %s

    """, (

        "VERIFIED",

        student_id

    ))


    conn.commit()

    cursor.close()

    conn.close()


    return redirect(
        "/admin/dashboard"
    )


# ==================================================
# REJECT PAYMENT
# ==================================================

@app.route(
    "/admin/reject/<int:student_id>",
    methods=["POST"]
)
def reject_payment(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            "/admin"
        )


    conn = get_db_connection()

    cursor = conn.cursor()


    cursor.execute("""
        UPDATE students

        SET payment_status = %s

        WHERE id = %s

    """, (

        "REJECTED",

        student_id

    ))


    conn.commit()

    cursor.close()

    conn.close()


    return redirect(
        "/admin/dashboard"
    )


# ==================================================
# ADMIN PAYMENT RECEIPT
# ==================================================

@app.route(
    "/admin/receipt/<int:student_id>"
)
def payment_receipt(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            "/admin"
        )


    conn = get_db_connection()

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

            participant_type,

            payment_amount

        FROM students

        WHERE id = %s

    """, (
        student_id,
    ))


    student = cursor.fetchone()


    cursor.close()

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
                Receipt केवल verified payment
                के बाद generate की जा सकती है।
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


# ==================================================
# STUDENT RECEIPT
# ==================================================

@app.route(
    "/student/receipt/<int:student_id>"
)
def student_receipt(student_id):

    conn = get_db_connection()

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

            participant_type,

            payment_amount

        FROM students

        WHERE id = %s

    """, (
        student_id,
    ))


    student = cursor.fetchone()


    cursor.close()

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
                Receipt केवल verified payment
                के बाद generate की जा सकती है।
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


# ==================================================
# ADMIN LOGOUT
# ==================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )


    return redirect(
        "/admin"
    )


# ==================================================
# START SERVER
# ==================================================

# ==================================================
# START SERVER
# ==================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),

        debug=False

    )