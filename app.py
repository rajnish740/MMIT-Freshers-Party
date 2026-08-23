from flask import Flask, render_template, request, redirect, session
import os
import psycopg2
import smtplib

from decimal import Decimal, InvalidOperation
from werkzeug.utils import secure_filename
from email.message import EmailMessage


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
# EMAIL NOTIFICATION
# ==================================================

def send_email_notification(
    recipient_email,
    student_name,
    registration_id,
    amount,
    status
):

    print("", flush=True)
    print("==========================================", flush=True)
    print("========== EMAIL DEBUG START ==========", flush=True)
    print("==========================================", flush=True)

    print(
        "Recipient:",
        repr(recipient_email),
        flush=True
    )

    print(
        "Student:",
        repr(student_name),
        flush=True
    )

    print(
        "Registration ID:",
        registration_id,
        flush=True
    )

    print(
        "Amount:",
        amount,
        flush=True
    )

    print(
        "Status:",
        status,
        flush=True
    )

    # ==================================================
    # CHECK STUDENT EMAIL
    # ==================================================

    if not recipient_email:

        print(
            "❌ ERROR: Student email is EMPTY.",
            flush=True
        )

        print(
            "========== EMAIL DEBUG END ==========",
            flush=True
        )

        return False


    # ==================================================
    # CLEAN EMAIL
    # ==================================================

    recipient_email = recipient_email.strip()


    if not recipient_email:

        print(
            "❌ ERROR: Student email became empty after strip().",
            flush=True
        )

        print(
            "========== EMAIL DEBUG END ==========",
            flush=True
        )

        return False


    # ==================================================
    # GET RENDER ENVIRONMENT VARIABLES
    # ==================================================

    sender_email = os.environ.get(
        "EMAIL_ADDRESS",
        ""
    ).strip()

    sender_password = os.environ.get(
        "EMAIL_APP_PASSWORD",
        ""
    ).strip()


    # ==================================================
    # CHECK EMAIL ADDRESS
    # ==================================================

    print(
        "EMAIL_ADDRESS found:",
        "YES" if sender_email else "NO",
        flush=True
    )


    if not sender_email:

        print(
            "❌ ERROR: EMAIL_ADDRESS is missing in Render Environment.",
            flush=True
        )

        print(
            "Please add EMAIL_ADDRESS in Render Environment Variables.",
            flush=True
        )

        print(
            "========== EMAIL DEBUG END ==========",
            flush=True
        )

        return False


    # ==================================================
    # CHECK APP PASSWORD
    # ==================================================

    print(
        "EMAIL_APP_PASSWORD found:",
        "YES" if sender_password else "NO",
        flush=True
    )


    if not sender_password:

        print(
            "❌ ERROR: EMAIL_APP_PASSWORD is missing in Render Environment.",
            flush=True
        )

        print(
            "Please add EMAIL_APP_PASSWORD in Render Environment Variables.",
            flush=True
        )

        print(
            "========== EMAIL DEBUG END ==========",
            flush=True
        )

        return False


    # ==================================================
    # DISPLAY EMAIL CONFIGURATION
    # ==================================================

    print(
        "Sender email:",
        sender_email,
        flush=True
    )

    print(
        "App password found: YES",
        flush=True
    )

    print(
        "App password length:",
        len(sender_password),
        flush=True
    )


    # ==================================================
    # EMAIL SUBJECT + BODY
    # ==================================================

    if status == "VERIFIED":

        subject = (
            "MMIT Freshers Party 2026 - "
            "Payment Verified"
        )

        body = f"""
Hello {student_name},

Your payment for MMIT Freshers Party 2026
has been successfully verified.

Registration No: {registration_id}
Amount: ₹{amount}
Payment Status: VERIFIED

Your registration is now confirmed.

Please keep this email for your records.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""


    elif status == "REJECTED":

        subject = (
            "MMIT Freshers Party 2026 - "
            "Payment Rejected"
        )

        body = f"""
Hello {student_name},

Your submitted payment for MMIT Freshers Party 2026
could not be verified.

Registration No: {registration_id}
Amount: ₹{amount}
Payment Status: REJECTED

Please contact the event administrator
and provide the correct payment details.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""


    else:

        print(
            "❌ ERROR: Invalid email status:",
            status,
            flush=True
        )

        print(
            "========== EMAIL DEBUG END ==========",
            flush=True
        )

        return False


    # ==================================================
    # CREATE EMAIL MESSAGE
    # ==================================================

    try:

        print(
            "Creating email message...",
            flush=True
        )

        message = EmailMessage()

        message["Subject"] = subject

        message["From"] = sender_email

        message["To"] = recipient_email

        message.set_content(body)

        print(
            "Email message created successfully.",
            flush=True
        )


        # ==================================================
        # CONNECT TO GMAIL SMTP
        # ==================================================

        print(
            "Connecting to Gmail SMTP...",
            flush=True
        )

        print(
            "SMTP Host: smtp.gmail.com",
            flush=True
        )

        print(
            "SMTP Port: 587",
            flush=True
        )


        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=30
        ) as server:

            print(
                "SMTP connection established.",
                flush=True
            )


            # ==================================================
            # EHLO
            # ==================================================

            print(
                "Sending EHLO...",
                flush=True
            )

            server.ehlo()

            print(
                "EHLO successful.",
                flush=True
            )


            # ==================================================
            # START TLS
            # ==================================================

            print(
                "Starting TLS...",
                flush=True
            )

            server.starttls()

            print(
                "TLS started successfully.",
                flush=True
            )


            # ==================================================
            # SECOND EHLO
            # ==================================================

            print(
                "Sending EHLO after TLS...",
                flush=True
            )

            server.ehlo()

            print(
                "EHLO after TLS successful.",
                flush=True
            )


            # ==================================================
            # LOGIN
            # ==================================================

            print(
                "Logging into Gmail...",
                flush=True
            )

            server.login(
                sender_email,
                sender_password
            )

            print(
                "✅ Gmail login successful.",
                flush=True
            )


            # ==================================================
            # SEND EMAIL
            # ==================================================

            print(
                "Sending email...",
                flush=True
            )

            server.send_message(
                message
            )

            print(
                "✅ EMAIL SENT SUCCESSFULLY!",
                flush=True
            )

            print(
                "Email sent to:",
                recipient_email,
                flush=True
            )


        # ==================================================
        # SUCCESS
        # ==================================================

        print(
            "==========================================",
            flush=True
        )

        print(
            "========== EMAIL DEBUG END ==========",
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        return True


    # ==================================================
    # EMAIL ERROR
    # ==================================================

    except smtplib.SMTPAuthenticationError as e:

        print("", flush=True)

        print(
            "==========================================",
            flush=True
        )

        print(
            "❌ GMAIL AUTHENTICATION ERROR",
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        print(
            "Gmail rejected the email/password.",
            flush=True
        )

        print(
            "Check EMAIL_ADDRESS and EMAIL_APP_PASSWORD.",
            flush=True
        )

        print(
            "Error:",
            repr(e),
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        return False


    except smtplib.SMTPConnectError as e:

        print("", flush=True)

        print(
            "==========================================",
            flush=True
        )

        print(
            "❌ SMTP CONNECTION ERROR",
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        print(
            "Could not connect to Gmail SMTP server.",
            flush=True
        )

        print(
            "Error:",
            repr(e),
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        return False


    except smtplib.SMTPException as e:

        print("", flush=True)

        print(
            "==========================================",
            flush=True
        )

        print(
            "❌ SMTP ERROR",
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        print(
            "Error:",
            repr(e),
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        return False


    except Exception as e:

        print("", flush=True)

        print(
            "==========================================",
            flush=True
        )

        print(
            "❌ EMAIL ERROR",
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        print(
            "Email sending error:",
            repr(e),
            flush=True
        )

        print(
            "Error type:",
            type(e).__name__,
            flush=True
        )

        print(
            "==========================================",
            flush=True
        )

        return False


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
    # ADD NEW COLUMNS
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

    print(
        "✅ Database initialized successfully.",
        flush=True
    )

except Exception as e:

    print(
        "❌ Database initialization error:",
        repr(e),
        flush=True
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


        # ==================================================
        # BASIC DETAILS
        # ==================================================

        name = request.form[
            "name"
        ].strip()


        participant_type = request.form[
            "participant_type"
        ].strip()


        # ==================================================
        # ROLL NUMBER
        # ==================================================

        roll_number = "N/A"


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


            # ==================================================
            # VALID YEAR
            # ==================================================

            if year not in [
                "1st Year",
                "2nd Year",
                "3rd Year"
            ]:

                return """
                <div style="
                    font-family: Arial;
                    text-align: center;
                    padding: 50px;
                ">

                    <h2>
                        ❌ Please select a valid Year.
                    </h2>

                    <a href="/register">
                        ← Back
                    </a>

                </div>
                """


            # ==================================================
            # STUDENT PAYMENT
            # ==================================================

            if year == "1st Year":

                payment_amount = Decimal("199")

            else:

                payment_amount = Decimal("300")


            # ==================================================
            # BRANCH VALIDATION
            # ==================================================

            if not branch:

                return """
                <div style="
                    font-family: Arial;
                    text-align: center;
                    padding: 50px;
                ">

                    <h2>
                        ❌ Branch is required.
                    </h2>

                    <a href="/register">
                        ← Back
                    </a>

                </div>
                """


        # ==================================================
        # TEACHER
        # ==================================================

        elif participant_type == "Teacher":


            if not teacher_amount:

                return """
                <div style="
                    font-family: Arial;
                    text-align: center;
                    padding: 50px;
                ">

                    <h2>
                        ❌ Teacher amount is required.
                    </h2>

                    <a href="/register">
                        ← Back
                    </a>

                </div>
                """


            try:

                payment_amount = Decimal(
                    teacher_amount
                )


            except InvalidOperation:

                return """
                <div style="
                    font-family: Arial;
                    text-align: center;
                    padding: 50px;
                ">

                    <h2>
                        ❌ Invalid teacher amount.
                    </h2>

                    <a href="/register">
                        ← Back
                    </a>

                </div>
                """


            if payment_amount <= 0:

                return """
                <div style="
                    font-family: Arial;
                    text-align: center;
                    padding: 50px;
                ">

                    <h2>
                        ❌ Amount must be greater than 0.
                    </h2>

                    <a href="/register">
                        ← Back
                    </a>

                </div>
                """


            year = "Teacher"


            if not branch:

                branch = "Teacher"


        # ==================================================
        # INVALID PARTICIPANT TYPE
        # ==================================================

        else:

            return """
            <div style="
                font-family: Arial;
                text-align: center;
                padding: 50px;
            ">

                <h2>
                    ❌ Invalid participant type.
                </h2>

                <a href="/register">
                    ← Back
                </a>

            </div>
            """


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


    # ==================================================
    # GET
    # ==================================================

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


    # ==================================================
    # UTR VALIDATION
    # ==================================================

    if not utr:

        return """
        <div style="
            font-family: Arial;
            text-align: center;
            padding: 50px;
        ">

            <h2>
                ❌ UTR / Transaction ID is required.
            </h2>

            <a href="javascript:history.back()">
                ← Back
            </a>

        </div>
        """


    # ==================================================
    # SCREENSHOT VALIDATION
    # ==================================================

    if (
        screenshot is None
        or screenshot.filename == ""
    ):

        return """
        <div style="
            font-family: Arial;
            text-align: center;
            padding: 50px;
        ">

            <h2>
                ❌ Payment screenshot is required.
            </h2>

            <a href="javascript:history.back()">
                ← Back
            </a>

        </div>
        """


    # ==================================================
    # FILE NAME
    # ==================================================

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


    screenshot.save(
        filepath
    )


    # ==================================================
    # UPDATE PAYMENT
    # ==================================================

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


    # ==================================================
    # SUCCESS
    # ==================================================

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
        # SHOW STATUS
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
        "ADMIN_PASSWORD"
    )


    if not ADMIN_PASSWORD:

        print(
            "WARNING: ADMIN_PASSWORD is not configured in Render.",
            flush=True
        )

        return """
        <div style="
            font-family: Arial;
            text-align: center;
            padding: 50px;
        ">

            <h2>
                ❌ Admin password is not configured.
            </h2>

            <p>
                Please set ADMIN_PASSWORD in Render Environment.
            </p>

        </div>
        """


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

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            "/admin"
        )


    conn = get_db_connection()

    cursor = conn.cursor()


    # ==================================================
    # ALL STUDENTS
    # ==================================================

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


    # ==================================================
    # VERIFIED PAYMENT TOTAL
    # ==================================================

    cursor.execute("""
        SELECT
            COALESCE(
                SUM(payment_amount),
                0
            )

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

    print("", flush=True)

    print(
        "==========================================",
        flush=True
    )

    print(
        "ADMIN VERIFY PAYMENT START",
        flush=True
    )

    print(
        "Student ID:",
        student_id,
        flush=True
    )


    if not session.get(
        "admin_logged_in"
    ):

        print(
            "❌ Admin session not found.",
            flush=True
        )

        return redirect(
            "/admin"
        )


    conn = get_db_connection()

    cursor = conn.cursor()


    # ==================================================
    # GET STUDENT EMAIL DETAILS
    # ==================================================

    print(
        "Getting student details from database...",
        flush=True
    )


    cursor.execute("""
        SELECT
            name,
            email,
            payment_amount

        FROM students

        WHERE id = %s
    """, (

        student_id,

    ))


    student = cursor.fetchone()


    if student is None:

        print(
            "❌ Student not found.",
            flush=True
        )

        cursor.close()

        conn.close()

        return "Student not found."


    student_name = student[0]

    student_email = student[1]

    payment_amount = student[2]


    print(
        "Student name:",
        student_name,
        flush=True
    )

    print(
        "Student email:",
        repr(student_email),
        flush=True
    )

    print(
        "Payment amount:",
        payment_amount,
        flush=True
    )


    # ==================================================
    # VERIFY PAYMENT
    # ==================================================

    print(
        "Updating payment status to VERIFIED...",
        flush=True
    )


    cursor.execute("""
        UPDATE students

        SET payment_status = %s

        WHERE id = %s
    """, (

        "VERIFIED",

        student_id

    ))


    conn.commit()


    print(
        "✅ Payment status saved as VERIFIED.",
        flush=True
    )


    cursor.close()

    conn.close()


    # ==================================================
    # SEND VERIFIED EMAIL
    # ==================================================

    print(
        "Calling send_email_notification()...",
        flush=True
    )


    email_result = send_email_notification(

        recipient_email=student_email,

        student_name=student_name,

        registration_id=student_id,

        amount=payment_amount,

        status="VERIFIED"

    )


    if email_result:

        print(
            "✅ Verified email process completed successfully.",
            flush=True
        )

    else:

        print(
            "⚠️ Verified payment saved, but email was NOT sent.",
            flush=True
        )


    print(
        "ADMIN VERIFY PAYMENT END",
        flush=True
    )

    print(
        "==========================================",
        flush=True
    )


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

    print("", flush=True)

    print(
        "==========================================",
        flush=True
    )

    print(
        "ADMIN REJECT PAYMENT START",
        flush=True
    )

    print(
        "Student ID:",
        student_id,
        flush=True
    )


    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            "/admin"
        )


    conn = get_db_connection()

    cursor = conn.cursor()


    # ==================================================
    # GET STUDENT EMAIL DETAILS
    # ==================================================

    cursor.execute("""
        SELECT
            name,
            email,
            payment_amount

        FROM students

        WHERE id = %s
    """, (

        student_id,

    ))


    student = cursor.fetchone()


    if student is None:

        print(
            "❌ Student not found.",
            flush=True
        )

        cursor.close()

        conn.close()

        return "Student not found."


    student_name = student[0]

    student_email = student[1]

    payment_amount = student[2]


    print(
        "Student name:",
        student_name,
        flush=True
    )

    print(
        "Student email:",
        repr(student_email),
        flush=True
    )

    print(
        "Payment amount:",
        payment_amount,
        flush=True
    )


    # ==================================================
    # REJECT PAYMENT
    # ==================================================

    cursor.execute("""
        UPDATE students

        SET payment_status = %s

        WHERE id = %s
    """, (

        "REJECTED",

        student_id

    ))


    conn.commit()


    print(
        "✅ Payment status saved as REJECTED.",
        flush=True
    )


    cursor.close()

    conn.close()


    # ==================================================
    # SEND REJECTED EMAIL
    # ==================================================

    print(
        "Calling send_email_notification()...",
        flush=True
    )


    email_result = send_email_notification(

        recipient_email=student_email,

        student_name=student_name,

        registration_id=student_id,

        amount=payment_amount,

        status="REJECTED"

    )


    if email_result:

        print(
            "✅ Rejected email process completed successfully.",
            flush=True
        )

    else:

        print(
            "⚠️ Rejected payment saved, but email was NOT sent.",
            flush=True
        )


    print(
        "ADMIN REJECT PAYMENT END",
        flush=True
    )

    print(
        "==========================================",
        flush=True
    )


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


    # ==================================================
    # ONLY VERIFIED PAYMENT
    # ==================================================

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


    # ==================================================
    # ONLY VERIFIED PAYMENT
    # ==================================================

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
