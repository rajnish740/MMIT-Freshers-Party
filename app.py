from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory,
    abort,
    redirect as flask_redirect,
)

import os
import re
import psycopg2
import requests

from decimal import Decimal, InvalidOperation
from werkzeug.utils import secure_filename


# ==================================================
# OPTIONAL CLOUDINARY IMPORT
# ==================================================

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    import cloudinary.utils

    CLOUDINARY_AVAILABLE = True

except ImportError:
    CLOUDINARY_AVAILABLE = False


# ==================================================
# APP
# ==================================================

app = Flask(
    __name__,
    static_folder=None
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)

UPLOAD_FOLDER = os.path.join(
    "static",
    "uploads"
)

LOCAL_STATIC_FOLDER = "static"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ==================================================
# CLOUDINARY CONFIGURATION
# ==================================================

CLOUDINARY_CLOUD_NAME = os.environ.get(
    "CLOUDINARY_CLOUD_NAME",
    ""
).strip()

CLOUDINARY_API_KEY = os.environ.get(
    "CLOUDINARY_API_KEY",
    ""
).strip()

CLOUDINARY_API_SECRET = os.environ.get(
    "CLOUDINARY_API_SECRET",
    ""
).strip()


CLOUDINARY_ENABLED = bool(
    CLOUDINARY_AVAILABLE
    and CLOUDINARY_CLOUD_NAME
    and CLOUDINARY_API_KEY
    and CLOUDINARY_API_SECRET
)


if CLOUDINARY_ENABLED:

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


print(
    "==========================================",
    flush=True
)

print(
    "CLOUDINARY CONFIGURATION",
    flush=True
)

print(
    "Cloudinary package:",
    "YES" if CLOUDINARY_AVAILABLE else "NO",
    flush=True
)

print(
    "Cloud name found:",
    "YES" if CLOUDINARY_CLOUD_NAME else "NO",
    flush=True
)

print(
    "API key found:",
    "YES" if CLOUDINARY_API_KEY else "NO",
    flush=True
)

print(
    "API secret found:",
    "YES" if CLOUDINARY_API_SECRET else "NO",
    flush=True
)

print(
    "Cloudinary enabled:",
    "YES" if CLOUDINARY_ENABLED else "NO",
    flush=True
)

print(
    "==========================================",
    flush=True
)


# ==================================================
# DATABASE
# ==================================================

def get_db_connection():

    database_url = os.environ.get(
        "DATABASE_URL"
    )

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    return psycopg2.connect(
        database_url,
        sslmode="require"
    )


# ==================================================
# EMAIL VALIDATION
# ==================================================

def is_valid_email(email):

    if not email:
        return False

    email = email.strip().lower()

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return bool(
        re.match(pattern, email)
    )


# ==================================================
# STATIC FILES
# ==================================================

@app.route(
    "/static/uploads/<path:filename>",
    endpoint="uploaded_file"
)
def uploaded_file(filename):

    filename = filename.strip()

    # ------------------------------------------
    # CLOUDINARY
    # ------------------------------------------

    if CLOUDINARY_ENABLED and filename:

        try:

            base_filename = os.path.splitext(
                filename
            )[0]

            public_id = (
                f"mmit_freshers/payments/{base_filename}"
            )

            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="image",
                secure=True,
            )[0]

            return flask_redirect(
                url,
                code=302
            )

        except Exception as e:

            print(
                "Cloudinary image redirect error:",
                repr(e),
                flush=True
            )

    # ------------------------------------------
    # LOCAL FALLBACK
    # ------------------------------------------

    local_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    if os.path.isfile(local_path):

        return send_from_directory(
            app.config["UPLOAD_FOLDER"],
            filename
        )

    abort(404)


# ==================================================
# IMPORTANT STATIC ROUTE
# ==================================================

@app.route(
    "/static/<path:filename>",
    endpoint="static"
)
def static_files(filename):

    return send_from_directory(
        LOCAL_STATIC_FOLDER,
        filename
    )


# ==================================================
# BREVO EMAIL
# ==================================================

def send_email_notification(
    recipient_email,
    student_name,
    registration_id,
    amount,
    status
):

    print(
        "==========================================",
        flush=True
    )

    print(
        "BREVO EMAIL START",
        flush=True
    )

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

    if not recipient_email:

        print(
            "❌ Student email is EMPTY.",
            flush=True
        )

        return False

    recipient_email = recipient_email.strip()

    if not recipient_email:

        print(
            "❌ Student email became empty.",
            flush=True
        )

        return False

    if not is_valid_email(recipient_email):

        print(
            "❌ Student email is invalid.",
            flush=True
        )

        return False

    brevo_api_key = os.environ.get(
        "BREVO_API_KEY",
        ""
    ).strip()

    brevo_sender_email = os.environ.get(
        "BREVO_SENDER_EMAIL",
        ""
    ).strip()

    brevo_sender_name = os.environ.get(
        "BREVO_SENDER_NAME",
        "MMIT Freshers Party 2026"
    ).strip()

    print(
        "BREVO_API_KEY found:",
        "YES" if brevo_api_key else "NO",
        flush=True
    )

    print(
        "BREVO_SENDER_EMAIL found:",
        "YES" if brevo_sender_email else "NO",
        flush=True
    )

    if not brevo_api_key:

        print(
            "❌ BREVO_API_KEY is missing.",
            flush=True
        )

        return False

    if not brevo_sender_email:

        print(
            "❌ BREVO_SENDER_EMAIL is missing.",
            flush=True
        )

        return False

    # ------------------------------------------
    # VERIFIED EMAIL
    # ------------------------------------------

    if status == "VERIFIED":

        subject = (
            "MMIT Freshers Party 2026 "
            "- Payment Verified"
        )

        body = f"""Hello {student_name},

Your payment for MMIT Freshers Party 2026 has been successfully verified.

Registration No: {registration_id}
Amount: ₹{amount}
Payment Status: VERIFIED

Your registration is now confirmed.

Please keep this email for your records.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""

    # ------------------------------------------
    # REJECTED EMAIL
    # ------------------------------------------

    elif status == "REJECTED":

        subject = (
            "MMIT Freshers Party 2026 "
            "- Payment Rejected"
        )

        body = f"""Hello {student_name},

Your submitted payment for MMIT Freshers Party 2026 could not be verified.

Registration No: {registration_id}
Amount: ₹{amount}
Payment Status: REJECTED

Please contact the event administrator and provide the correct payment details.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""

    else:

        print(
            "❌ Invalid email status:",
            status,
            flush=True
        )

        return False

    # ------------------------------------------
    # BREVO API
    # ------------------------------------------

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": brevo_api_key,
        "content-type": "application/json",
    }

    payload = {

        "sender": {
            "name": brevo_sender_name,
            "email": brevo_sender_email,
        },

        "to": [
            {
                "email": recipient_email,
                "name": student_name,
            }
        ],

        "subject": subject,

        "textContent": body,
    }

    try:

        print(
            "Sending email through Brevo API...",
            flush=True
        )

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(
            "Brevo HTTP Status:",
            response.status_code,
            flush=True
        )

        if response.status_code == 201:

            try:

                data = response.json()

                print(
                    "Brevo Message ID:",
                    data.get("messageId"),
                    flush=True
                )

            except Exception:
                pass

            print(
                "✅ EMAIL SENT SUCCESSFULLY!",
                flush=True
            )

            return True

        print(
            "❌ BREVO EMAIL FAILED",
            flush=True
        )

        print(
            "Brevo response:",
            response.text,
            flush=True
        )

        return False

    except requests.exceptions.Timeout:

        print(
            "❌ BREVO API TIMEOUT",
            flush=True
        )

        return False

    except requests.exceptions.RequestException as e:

        print(
            "❌ BREVO API CONNECTION ERROR:",
            repr(e),
            flush=True
        )

        return False

    except Exception as e:

        print(
            "❌ BREVO EMAIL ERROR:",
            repr(e),
            flush=True
        )

        return False


# ==================================================
# CLOUDINARY UPLOAD
# ==================================================

def upload_payment_to_cloudinary(
    file_obj,
    student_id
):

    if not CLOUDINARY_ENABLED:

        print(
            "⚠️ Cloudinary is not configured; using local upload.",
            flush=True
        )

        return None

    original_name = secure_filename(
        file_obj.filename or "payment.jpg"
    )

    if not original_name:

        original_name = "payment.jpg"

    stored_filename = (
        f"{student_id}_{original_name}"
    )

    base_name = os.path.splitext(
        stored_filename
    )[0]

    try:

        print(
            "Uploading payment screenshot to Cloudinary...",
            flush=True
        )

        result = cloudinary.uploader.upload(
            file_obj,
            folder="mmit_freshers/payments",
            public_id=base_name,
            resource_type="image",
            overwrite=True,
            unique_filename=False,
        )

        public_id = result.get(
            "public_id",
            ""
        )

        secure_url = result.get(
            "secure_url",
            ""
        )

        print(
            "Cloudinary public_id:",
            public_id,
            flush=True
        )

        print(
            "Cloudinary URL created:",
            "YES" if secure_url else "NO",
            flush=True
        )

        return stored_filename

    except Exception as e:

        print(
            "❌ Cloudinary upload failed:",
            repr(e),
            flush=True
        )

        return None


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def create_database():

    conn = get_db_connection()

    cursor = conn.cursor()

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

    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS participant_type TEXT
    """)

    cursor.execute("""
        ALTER TABLE students
        ADD COLUMN IF NOT EXISTS payment_amount NUMERIC(10,2)
    """)

    conn.commit()

    # ==================================================
    # UNIQUE MOBILE
    # ==================================================

    try:

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            unique_student_mobile
            ON students (mobile)
        """)

        conn.commit()

        print(
            "✅ Unique mobile protection enabled.",
            flush=True
        )

    except Exception as e:

        conn.rollback()

        print(
            "⚠️ Mobile unique index could not be created:",
            repr(e),
            flush=True
        )

    # ==================================================
    # UNIQUE EMAIL
    # ==================================================

    try:

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            unique_student_email
            ON students (LOWER(email))
            WHERE email IS NOT NULL
              AND email <> ''
        """)

        conn.commit()

        print(
            "✅ Unique email protection enabled.",
            flush=True
        )

    except Exception as e:

        conn.rollback()

        print(
            "⚠️ Email unique index could not be created:",
            repr(e),
            flush=True
        )

    # ==================================================
    # UNIQUE UTR
    # ==================================================

    try:

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            unique_student_utr
            ON students (LOWER(utr))
            WHERE utr IS NOT NULL
              AND utr <> ''
        """)

        conn.commit()

        print(
            "✅ Unique UTR protection enabled.",
            flush=True
        )

    except Exception as e:

        conn.rollback()

        print(
            "⚠️ UTR unique index could not be created:",
            repr(e),
            flush=True
        )

    cursor.close()

    conn.close()


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

        name = request.form.get(
            "name",
            ""
        ).strip()

        participant_type = request.form.get(
            "participant_type",
            ""
        ).strip()

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

        mobile = request.form.get(
            "mobile",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        gender = request.form.get(
            "gender",
            ""
        ).strip()

        # ==================================================
        # REQUIRED FIELD VALIDATION
        # ==================================================

        if not name:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Name is required.</h2>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        if not mobile:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Mobile Number is required.</h2>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        if not email:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Email is required.</h2>

                <p>
                    Payment करने के लिए valid email देना जरूरी है।
                </p>

                <br>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        if not gender:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Gender is required.</h2>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        # ==================================================
        # EMAIL FORMAT
        # ==================================================

        if not is_valid_email(email):

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Invalid Email Address</h2>

                <p>
                    कृपया valid email address डालें।
                </p>

                <p>
                    Example: student@gmail.com
                </p>

                <br>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        # ==================================================
        # MOBILE FORMAT
        # ==================================================

        if not mobile.isdigit() or len(mobile) != 10:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Invalid Mobile Number</h2>

                <p>
                    कृपया 10 digit valid mobile number डालें।
                </p>

                <br>

                <a href="/register">
                    ← Back
                </a>

            </div>
            """

        # ==================================================
        # DATABASE DUPLICATE CHECK
        # ==================================================

        conn = get_db_connection()

        cursor = conn.cursor()

        # ------------------------------------------
        # MOBILE
        # ------------------------------------------

        cursor.execute("""
            SELECT id, name
            FROM students
            WHERE mobile = %s
            LIMIT 1
        """, (
            mobile,
        ))

        existing_mobile = cursor.fetchone()

        # ------------------------------------------
        # EMAIL
        # ------------------------------------------

        cursor.execute("""
            SELECT id, name
            FROM students
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
        """, (
            email,
        ))

        existing_email = cursor.fetchone()

        cursor.close()

        conn.close()

        # ==================================================
        # DUPLICATE MOBILE
        # ==================================================

        if existing_mobile:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Mobile Number Already Registered</h2>

                <p>
                    यह mobile number पहले से registration
                    में इस्तेमाल हो चुका है।
                </p>

                <p>
                    एक mobile number से केवल एक ही payment
                    registration किया जा सकता है।
                </p>

                <br>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        # ==================================================
        # DUPLICATE EMAIL
        # ==================================================

        if existing_email:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Email Already Registered</h2>

                <p>
                    यह email पहले से registration
                    में इस्तेमाल हो चुका है।
                </p>

                <p>
                    एक email से केवल एक ही payment
                    registration किया जा सकता है।
                </p>

                <br>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        # ==================================================
        # STUDENT
        # ==================================================

        if participant_type == "Student":

            if year not in [
                "1st Year",
                "2nd Year",
                "3rd Year"
            ]:

                return (
                    "❌ Please select a valid Year. "
                    "<a href='/register'>Back</a>"
                )

            # ------------------------------------------
            # FEE
            # ------------------------------------------

            payment_amount = (
                Decimal("199")
                if year == "1st Year"
                else Decimal("300")
            )

            if not branch:

                return (
                    "❌ Branch is required. "
                    "<a href='/register'>Back</a>"
                )

        # ==================================================
        # TEACHER
        # ==================================================

        elif participant_type == "Teacher":

            if not teacher_amount:

                return (
                    "❌ Teacher amount is required. "
                    "<a href='/register'>Back</a>"
                )

            try:

                payment_amount = Decimal(
                    teacher_amount
                )

            except InvalidOperation:

                return (
                    "❌ Invalid teacher amount. "
                    "<a href='/register'>Back</a>"
                )

            if payment_amount <= 0:

                return (
                    "❌ Amount must be greater than 0. "
                    "<a href='/register'>Back</a>"
                )

            year = "Teacher"

            if not branch:

                branch = "Teacher"

        else:

            return (
                "❌ Invalid participant type. "
                "<a href='/register'>Back</a>"
            )

        # ==================================================
        # INSERT REGISTRATION
        # ==================================================

        conn = get_db_connection()

        cursor = conn.cursor()

        try:

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
                payment_amount,
            ))

            registration_id = cursor.fetchone()[0]

            conn.commit()

        except psycopg2.errors.UniqueViolation:

            conn.rollback()

            cursor.close()

            conn.close()

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Duplicate Registration</h2>

                <p>
                    Mobile Number या Email पहले से registered है।
                </p>

                <p>
                    एक व्यक्ति के लिए केवल एक registration
                    allowed है।
                </p>

                <br>

                <a href="/register">
                    ← Back to Registration
                </a>

            </div>
            """

        except Exception as e:

            conn.rollback()

            print(
                "❌ Registration INSERT error:",
                repr(e),
                flush=True
            )

            cursor.close()

            conn.close()

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Registration Failed</h2>

                <p>
                    Registration करते समय error आया।
                </p>

                <br>

                <a href="/register">
                    ← Back
                </a>

            </div>
            """

        cursor.close()

        conn.close()

        return render_template(
            "payment.html",
            registration_no=registration_id,
            student_name=name,
            amount=payment_amount,
            participant_type=participant_type,
            year=year,
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
            email,
            payment_amount,
            payment_status
        FROM students
        WHERE id = %s
    """, (
        student_id,
    ))

    student = cursor.fetchone()

    cursor.close()

    conn.close()

    # ==================================================
    # REGISTRATION CHECK
    # ==================================================

    if student is None:

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Registration Not Found</h2>

            <a href="/register">
                ← Back to Registration
            </a>

        </div>
        """

    # ==================================================
    # EMAIL SECURITY CHECK
    # ==================================================

    student_email = student[2]

    if not student_email or not student_email.strip():

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Payment Blocked</h2>

            <p>
                इस registration में email address मौजूद नहीं है।
            </p>

            <p>
                बिना email के payment submit नहीं की जा सकती।
            </p>

            <br>

            <a href="/register">
                ← New Registration
            </a>

        </div>
        """

    # ==================================================
    # EMAIL FORMAT SECURITY CHECK
    # ==================================================

    if not is_valid_email(student_email):

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Invalid Email</h2>

            <p>
                इस registration का email valid नहीं है।
            </p>

            <p>
                Payment submit नहीं की जा सकती।
            </p>

            <br>

            <a href="/register">
                ← New Registration
            </a>

        </div>
        """

    # ==================================================
    # PAYMENT STATUS CHECK
    # ==================================================

    if student[4] in [
        "SUBMITTED",
        "VERIFIED"
    ]:

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>⚠️ Payment Already Submitted</h2>

            <p>
                इस registration के लिए payment details
                पहले ही submit हो चुकी हैं।
            </p>

            <br>

            <a href="/payment-status">
                🔍 Check Payment Status
            </a>

        </div>
        """

    return render_template(
        "payment_submit.html",
        registration_id=student[0],
        student_id=student[0],
        student_name=student[1],
        email=student_email,
        amount=student[3],
    )


# ==================================================
# SAVE PAYMENT DETAILS + CLOUDINARY
# ==================================================

@app.route(
    "/payment-submit",
    methods=["POST"]
)
def save_payment():

    student_id = request.form.get(
        "student_id",
        ""
    ).strip()

    utr = request.form.get(
        "utr",
        ""
    ).strip()

    screenshot = request.files.get(
        "payment_screenshot"
    )

    # ==================================================
    # BASIC SECURITY
    # ==================================================

    if not student_id:

        return (
            "❌ Student ID is missing."
        )

    if not student_id.isdigit():

        return (
            "❌ Invalid Student ID."
        )

    if not utr:

        return (
            "❌ UTR / Transaction ID is required. "
            "<a href='javascript:history.back()'>Back</a>"
        )

    if (
        screenshot is None
        or screenshot.filename == ""
    ):

        return (
            "❌ Payment screenshot is required. "
            "<a href='javascript:history.back()'>Back</a>"
        )

    # ==================================================
    # CHECK REGISTRATION
    # ==================================================

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            payment_status,
            payment_amount
        FROM students
        WHERE id = %s
    """, (
        student_id,
    ))

    student = cursor.fetchone()

    # ==================================================
    # REGISTRATION NOT FOUND
    # ==================================================

    if not student:

        cursor.close()

        conn.close()

        return (
            "❌ Registration not found."
        )

    # ==================================================
    # EMAIL SECURITY CHECK
    # ==================================================

    student_email = student[2]

    if not student_email or not student_email.strip():

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Payment Blocked</h2>

            <p>
                इस registration में email address मौजूद नहीं है।
            </p>

            <p>
                बिना email के payment submit नहीं की जा सकती।
            </p>

            <br>

            <a href="/register">
                ← New Registration
            </a>

        </div>
        """

    # ==================================================
    # EMAIL FORMAT CHECK
    # ==================================================

    if not is_valid_email(student_email):

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Invalid Email</h2>

            <p>
                Registration में valid email नहीं है।
            </p>

            <p>
                Payment submit नहीं की जा सकती।
            </p>

            <br>

            <a href="/register">
                ← New Registration
            </a>

        </div>
        """

    # ==================================================
    # CHECK PAYMENT STATUS
    # ==================================================

    if student[3] in [
        "SUBMITTED",
        "VERIFIED"
    ]:

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>⚠️ Payment Already Submitted</h2>

            <p>
                इस registration के लिए payment details
                पहले ही submit हो चुकी हैं।
            </p>

            <p>
                Duplicate payment submit नहीं किया जा सकता।
            </p>

            <br>

            <a href="/">
                ← Back to Home
            </a>

        </div>
        """

    # ==================================================
    # CHECK DUPLICATE UTR
    # ==================================================

    cursor.execute("""
        SELECT
            id,
            name
        FROM students
        WHERE LOWER(utr) = LOWER(%s)
        LIMIT 1
    """, (
        utr,
    ))

    existing_utr = cursor.fetchone()

    if existing_utr:

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ UTR Already Used</h2>

            <p>
                यह UTR / Transaction ID पहले से किसी
                registration में इस्तेमाल हो चुका है।
            </p>

            <p>
                एक UTR से केवल एक payment स्वीकार की जाएगी।
            </p>

            <br>

            <a href="javascript:history.back()">
                ← Back
            </a>

        </div>
        """

    cursor.close()

    conn.close()

    # ==================================================
    # SCREENSHOT UPLOAD
    # ==================================================

    filename = None

    # ------------------------------------------
    # CLOUDINARY
    # ------------------------------------------

    if CLOUDINARY_ENABLED:

        filename = upload_payment_to_cloudinary(
            screenshot,
            student_id
        )

        if not filename:

            return (
                "❌ Payment screenshot could not "
                "be uploaded. Please try again."
            )

    # ------------------------------------------
    # LOCAL FALLBACK
    # ------------------------------------------

    else:

        original_name = secure_filename(
            screenshot.filename
        )

        if not original_name:

            return (
                "❌ Invalid screenshot filename."
            )

        filename = (
            f"{student_id}_{original_name}"
        )

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        screenshot.save(filepath)

        print(
            "⚠️ Screenshot saved locally:",
            filepath,
            flush=True
        )

    # ==================================================
    # DATABASE UPDATE
    # ==================================================

    conn = get_db_connection()

    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE students
            SET
                payment_status = %s,
                utr = %s,
                payment_screenshot = %s
            WHERE id = %s
              AND payment_status = 'PENDING'
              AND email IS NOT NULL
              AND email <> ''
        """, (
            "SUBMITTED",
            utr,
            filename,
            student_id,
        ))

        if cursor.rowcount != 1:

            conn.rollback()

            cursor.close()

            conn.close()

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Payment Submission Blocked</h2>

                <p>
                    Registration invalid है या payment
                    पहले ही submit हो चुकी है।
                </p>

                <br>

                <a href="/">
                    ← Back to Home
                </a>

            </div>
            """

        conn.commit()

    except psycopg2.errors.UniqueViolation:

        conn.rollback()

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Duplicate UTR</h2>

            <p>
                यह UTR पहले से registered है।
            </p>

            <p>
                कृपया सही UTR / Transaction ID डालें।
            </p>

            <br>

            <a href="javascript:history.back()">
                ← Back
            </a>

        </div>
        """

    except Exception as e:

        conn.rollback()

        print(
            "❌ Payment update error:",
            repr(e),
            flush=True
        )

        cursor.close()

        conn.close()

        return (
            "❌ Payment details save नहीं हो सके।"
        )

    cursor.close()

    conn.close()

    # ==================================================
    # SUCCESS
    # ==================================================

    return """
    <div style="
        font-family:Arial;
        text-align:center;
        padding:50px
    ">

        <h1>🎉 Payment Details Submitted!</h1>

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
            WHERE LOWER(utr) = LOWER(%s)
              AND mobile = %s
        """, (
            utr,
            mobile,
        ))

        student = cursor.fetchone()

        cursor.close()

        conn.close()

        if student is None:

            return render_template(
                "student_status.html",
                error=(
                    "❌ UTR / Transaction ID "
                    "या Mobile Number गलत है।"
                )
            )

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

    username = request.form.get(
        "username",
        ""
    )

    password = request.form.get(
        "password",
        ""
    )

    admin_username = os.environ.get(
        "ADMIN_USERNAME",
        "brijesh"
    )

    admin_password = os.environ.get(
        "ADMIN_PASSWORD"
    )

    if not admin_password:

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px
        ">

            <h2>
                ❌ Admin password is not configured.
            </h2>

            <p>
                Please set ADMIN_PASSWORD
                in Render Environment Variables.
            </p>

        </div>
        """

    if (
        username == admin_username
        and password == admin_password
    ):

        session["admin_logged_in"] = True

        return redirect(
            "/admin/dashboard"
        )

    return """
    <div style="
        font-family:Arial;
        text-align:center;
        padding:50px
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

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect("/admin")

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
            payment_screenshot,
            participant_type,
            payment_amount
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

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
        total_collection=total_collection,
    )


# ==================================================
# VERIFY PAYMENT + BREVO
# ==================================================

@app.route(
    "/admin/verify/<int:student_id>",
    methods=["POST"]
)
def verify_payment(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect("/admin")

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            email,
            payment_amount,
            payment_status
        FROM students
        WHERE id = %s
    """, (
        student_id,
    ))

    student = cursor.fetchone()

    if student is None:

        cursor.close()

        conn.close()

        return "Student not found."

    student_name = student[0]

    student_email = student[1]

    payment_amount = student[2]

    payment_status = student[3]

    # ==================================================
    # VERIFY ONLY SUBMITTED PAYMENT
    # ==================================================

    if payment_status != "SUBMITTED":

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Cannot Verify Payment</h2>

            <p>
                यह payment अभी SUBMITTED status में नहीं है।
            </p>

            <br>

            <a href="/admin/dashboard">
                ← Back to Dashboard
            </a>

        </div>
        """

    # ==================================================
    # EMAIL MUST EXIST
    # ==================================================

    if not student_email or not is_valid_email(student_email):

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Verification Blocked</h2>

            <p>
                Student का valid email मौजूद नहीं है।
            </p>

            <p>
                Payment verify नहीं की जा सकती।
            </p>

            <br>

            <a href="/admin/dashboard">
                ← Back to Dashboard
            </a>

        </div>
        """

    cursor.execute("""
        UPDATE students
        SET payment_status = %s
        WHERE id = %s
          AND payment_status = 'SUBMITTED'
          AND email IS NOT NULL
          AND email <> ''
    """, (
        "VERIFIED",
        student_id,
    ))

    if cursor.rowcount != 1:

        conn.rollback()

        cursor.close()

        conn.close()

        return "❌ Payment verification failed."

    conn.commit()

    cursor.close()

    conn.close()

    print(
        "✅ Payment status saved as VERIFIED.",
        flush=True
    )

    email_result = send_email_notification(
        recipient_email=student_email,
        student_name=student_name,
        registration_id=student_id,
        amount=payment_amount,
        status="VERIFIED",
    )

    if email_result:

        print(
            "✅ Verified email sent.",
            flush=True
        )

    else:

        print(
            "⚠️ Payment verified, but email was NOT sent.",
            flush=True
        )

    return redirect(
        "/admin/dashboard"
    )


# ==================================================
# REJECT PAYMENT + BREVO
# ==================================================

@app.route(
    "/admin/reject/<int:student_id>",
    methods=["POST"]
)
def reject_payment(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect("/admin")

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            email,
            payment_amount,
            payment_status
        FROM students
        WHERE id = %s
    """, (
        student_id,
    ))

    student = cursor.fetchone()

    if student is None:

        cursor.close()

        conn.close()

        return "Student not found."

    student_name = student[0]

    student_email = student[1]

    payment_amount = student[2]

    payment_status = student[3]

    if payment_status != "SUBMITTED":

        cursor.close()

        conn.close()

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Cannot Reject Payment</h2>

            <p>
                यह payment SUBMITTED status में नहीं है।
            </p>

            <br>

            <a href="/admin/dashboard">
                ← Back to Dashboard
            </a>

        </div>
        """

    cursor.execute("""
        UPDATE students
        SET payment_status = %s
        WHERE id = %s
          AND payment_status = 'SUBMITTED'
    """, (
        "REJECTED",
        student_id,
    ))

    if cursor.rowcount != 1:

        conn.rollback()

        cursor.close()

        conn.close()

        return "❌ Payment rejection failed."

    conn.commit()

    cursor.close()

    conn.close()

    print(
        "✅ Payment status saved as REJECTED.",
        flush=True
    )

    email_result = send_email_notification(
        recipient_email=student_email,
        student_name=student_name,
        registration_id=student_id,
        amount=payment_amount,
        status="REJECTED",
    )

    if email_result:

        print(
            "✅ Rejected email sent.",
            flush=True
        )

    else:

        print(
            "⚠️ Payment rejected, but email was NOT sent.",
            flush=True
        )

    return redirect(
        "/admin/dashboard"
    )


# ==================================================
# ADMIN DELETE ONE REGISTRATION
# ==================================================

@app.route(
    "/admin/delete/<int:student_id>",
    methods=["POST"]
)
def delete_student(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect("/admin")

    conn = None

    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                name,
                payment_screenshot
            FROM students
            WHERE id = %s
        """, (
            student_id,
        ))

        student = cursor.fetchone()

        if student is None:

            return """
            <div style="
                font-family:Arial;
                text-align:center;
                padding:50px;
            ">

                <h2>❌ Student Not Found</h2>

                <a href="/admin/dashboard">
                    ← Back to Dashboard
                </a>

            </div>
            """

        screenshot_filename = student[2]

        cursor.execute("""
            DELETE FROM students
            WHERE id = %s
        """, (
            student_id,
        ))

        conn.commit()

        # ------------------------------------------
        # LOCAL
        # ------------------------------------------

        if screenshot_filename:

            local_file = os.path.join(
                app.config["UPLOAD_FOLDER"],
                screenshot_filename
            )

            if os.path.isfile(local_file):

                try:

                    os.remove(local_file)

                except Exception as e:

                    print(
                        "⚠️ Local delete error:",
                        repr(e),
                        flush=True
                    )

        # ------------------------------------------
        # CLOUDINARY
        # ------------------------------------------

        if (
            CLOUDINARY_ENABLED
            and screenshot_filename
        ):

            try:

                base_filename = os.path.splitext(
                    screenshot_filename
                )[0]

                public_id = (
                    f"mmit_freshers/payments/"
                    f"{base_filename}"
                )

                cloudinary.uploader.destroy(
                    public_id,
                    resource_type="image"
                )

            except Exception as e:

                print(
                    "⚠️ Cloudinary delete error:",
                    repr(e),
                    flush=True
                )

        return redirect(
            "/admin/dashboard"
        )

    except Exception as e:

        if conn:

            conn.rollback()

        print(
            "❌ DELETE STUDENT ERROR:",
            repr(e),
            flush=True
        )

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Delete Failed</h2>

            <a href="/admin/dashboard">
                ← Back to Dashboard
            </a>

        </div>
        """

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()


# ==================================================
# ADMIN DELETE ALL REGISTRATIONS
# ==================================================

@app.route(
    "/admin/delete-all",
    methods=["POST"]
)
def delete_all_students():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect("/admin")

    conn = None

    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        cursor.execute("""
            SELECT payment_screenshot
            FROM students
            WHERE payment_screenshot IS NOT NULL
        """)

        screenshots = cursor.fetchall()

        cursor.execute("""
            DELETE FROM students
        """)

        cursor.execute("""
            ALTER SEQUENCE students_id_seq
            RESTART WITH 1
        """)

        conn.commit()

        # ------------------------------------------
        # LOCAL FILES
        # ------------------------------------------

        for screenshot in screenshots:

            filename = screenshot[0]

            if not filename:

                continue

            local_file = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            if os.path.isfile(local_file):

                try:

                    os.remove(local_file)

                except Exception as e:

                    print(
                        "⚠️ Local file delete error:",
                        repr(e),
                        flush=True
                    )

        # ------------------------------------------
        # CLOUDINARY FILES
        # ------------------------------------------

        if CLOUDINARY_ENABLED:

            for screenshot in screenshots:

                filename = screenshot[0]

                if not filename:

                    continue

                try:

                    base_filename = os.path.splitext(
                        filename
                    )[0]

                    public_id = (
                        f"mmit_freshers/payments/"
                        f"{base_filename}"
                    )

                    cloudinary.uploader.destroy(
                        public_id,
                        resource_type="image"
                    )

                except Exception as e:

                    print(
                        "⚠️ Cloudinary delete error:",
                        repr(e),
                        flush=True
                    )

        return redirect(
            "/admin/dashboard"
        )

    except Exception as e:

        if conn:

            conn.rollback()

        print(
            "❌ DELETE ALL ERROR:",
            repr(e),
            flush=True
        )

        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>❌ Delete All Failed</h2>

            <a href="/admin/dashboard">
                ← Back to Dashboard
            </a>

        </div>
        """

    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()


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

        return redirect("/admin")

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
            font-family:Arial;
            text-align:center;
            padding:50px
        ">

            <h2>
                ⚠️ Payment Not Verified
            </h2>

            <p>
                Receipt केवल verified payment
                के बाद generate की जा सकती है।
            </p>

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
            font-family:Arial;
            text-align:center;
            padding:50px
        ">

            <h2>
                ⚠️ Payment Not Verified
            </h2>

            <p>
                Receipt केवल verified payment
                के बाद generate की जा सकती है।
            </p>

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

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect("/admin")


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

        debug=False,
    )