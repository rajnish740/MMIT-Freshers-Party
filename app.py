from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory,
    abort,
)

import os
import re
import uuid
import html
import requests
import psycopg2

from decimal import Decimal, InvalidOperation
from datetime import timedelta
from werkzeug.utils import secure_filename


# ============================================================
# OPTIONAL CLOUDINARY
# ============================================================

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.utils

    CLOUDINARY_AVAILABLE = True

except ImportError:
    CLOUDINARY_AVAILABLE = False


# ============================================================
# APP
# ============================================================

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

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

if os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True

app.permanent_session_lifetime = timedelta(
    minutes=60
)

# ============================================================
# SECURITY HEADERS
# ============================================================

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    # HTTPS site ke liye HSTS
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000"
    )

    return response
# ============================================================
# BASE URL
# ============================================================

APP_BASE_URL = os.environ.get(
    "APP_BASE_URL",
    ""
).strip().rstrip("/")


def get_base_url():

    if APP_BASE_URL:
        return APP_BASE_URL

    try:
        return request.url_root.rstrip("/")

    except Exception:
        return ""


# ============================================================
# REGISTRATION NUMBER
# ============================================================

def format_registration_no(registration_id):

    try:

        return f"MMIT-2026-{int(registration_id):04d}"

    except (TypeError, ValueError):

        return str(registration_id or "")


# ============================================================
# CLOUDINARY CONFIG
# ============================================================

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


print("=" * 60)

print(
    "CLOUDINARY:",
    "ENABLED" if CLOUDINARY_ENABLED else "DISABLED"
)

print("=" * 60)


# ============================================================
# IMAGE VALIDATION
# ============================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}


def allowed_image(filename):

    if not filename:
        return False

    filename = filename.lower().strip()

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1]

    return extension in ALLOWED_IMAGE_EXTENSIONS


# ============================================================
# DATABASE
# ============================================================

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


# ============================================================
# EMAIL VALIDATION
# ============================================================

def is_valid_email(email):

    if not email:
        return False

    email = email.strip().lower()

    return bool(
        re.match(
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
            email
        )
    )


# ============================================================
# STATIC UPLOAD ROUTE
# ============================================================

@app.route(
    "/static/uploads/<path:filename>",
    endpoint="uploaded_file"
)
def uploaded_file(filename):

    filename = filename.strip()

    if CLOUDINARY_ENABLED and filename:

        try:

            base_filename = os.path.splitext(
                filename
            )[0]

            public_id = (
                f"mmit_freshers/payments/"
                f"{base_filename}"
            )

            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type="image",
                secure=True,
            )[0]

            return redirect(url)

        except Exception as e:

            print(
                "Cloudinary image error:",
                repr(e)
            )

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


# ============================================================
# STATIC ROUTE
# ============================================================

@app.route(
    "/static/<path:filename>",
    endpoint="static"
)
def static_files(filename):

    return send_from_directory(
        LOCAL_STATIC_FOLDER,
        filename
    )


# ============================================================
# BREVO EMAIL
# ============================================================

def send_email_notification(
    recipient_email,
    student_name,
    registration_id,
    amount,
    utr,
    status
):

    if not recipient_email:
        print("Student email missing.")
        return False

    recipient_email = recipient_email.strip()

    if not is_valid_email(recipient_email):
        print("Invalid student email.")
        return False

    brevo_api_key = os.environ.get(
        "BREVO_API_KEY",
        ""
    ).strip()

    sender_email = os.environ.get(
        "BREVO_SENDER_EMAIL",
        ""
    ).strip()

    sender_name = os.environ.get(
        "BREVO_SENDER_NAME",
        "MMIT Freshers Party 2026"
    ).strip()

    if not brevo_api_key:
        print("BREVO_API_KEY missing.")
        return False

    if not sender_email or not is_valid_email(sender_email):
        print("BREVO_SENDER_EMAIL missing/invalid.")
        return False

    # ========================================================
    # SAFE STUDENT NAME
    # ========================================================

    raw_name = str(student_name or "").strip()

    first_name = (
        raw_name.split()[0]
        if raw_name
        else "Student"
    )

    display_name = (
        first_name[:1].upper()
        + first_name[1:].lower()
    )

    # ========================================================
    # AMOUNT
    # ========================================================

    try:

        formatted_amount = Decimal(
            str(amount or "0")
        ).quantize(
            Decimal("0.01")
        )

    except Exception:

        formatted_amount = Decimal("0.00")

    amount_display = f"{formatted_amount:.2f}"

    # ========================================================
    # REGISTRATION NUMBER
    # ========================================================

    # Important:
    # Agar caller already MMIT-2026-0012 bhej raha hai,
    # to dobara MMIT-2026 lagne se bachayenge.

    registration_display = str(
        registration_id or ""
    ).strip()

    if not registration_display.startswith("MMIT-2026-"):

        registration_display = format_registration_no(
            registration_id
        )

    # ========================================================
    # VERIFIED EMAIL
    # ========================================================

    if status == "VERIFIED":

        subject = (
            "MMIT Freshers Party 2026 - "
            "Payment Verified Successfully"
        )

        body = f"""Hello {display_name},

Your payment for MMIT Freshers Party 2026 has been successfully verified.

Registration No: {registration_display}
Amount: Rs. {amount_display}
UTR / Transaction ID: {utr or "Not Available"}
Payment Status: VERIFIED

Your registration is now confirmed.

Please keep this email for your records.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Payment Verified</title>
</head>

<body style="
margin:0;
padding:0;
background:#f4f6f8;
font-family:Arial,Helvetica,sans-serif;
color:#222;
">

<div style="
max-width:650px;
margin:30px auto;
background:#ffffff;
padding:30px;
border-radius:14px;
box-shadow:0 4px 18px rgba(0,0,0,0.08);
">

<h2 style="
margin-top:0;
color:#198754;
">
MMIT Freshers Party 2026
</h2>

<p>
Hello
<strong>{html.escape(display_name)}</strong>,
</p>

<p>
Your payment for
<strong>MMIT Freshers Party 2026</strong>
has been successfully verified.
</p>

<table
width="100%"
cellpadding="12"
style="
border-collapse:collapse;
margin-top:20px;
margin-bottom:20px;
">

<tr>
<td style="border:1px solid #ddd;">
<strong>Registration No.</strong>
</td>

<td style="border:1px solid #ddd;">
{html.escape(registration_display)}
</td>
</tr>

<tr>
<td style="border:1px solid #ddd;">
<strong>Amount</strong>
</td>

<td style="border:1px solid #ddd;">
Rs. {html.escape(amount_display)}
</td>
</tr>

<tr>
<td style="border:1px solid #ddd;">
<strong>UTR / Transaction ID</strong>
</td>

<td style="border:1px solid #ddd;">
{html.escape(str(utr or "Not Available"))}
</td>
</tr>

<tr>
<td style="border:1px solid #ddd;">
<strong>Payment Status</strong>
</td>

<td style="
border:1px solid #ddd;
color:#198754;
">

<strong>VERIFIED</strong>

</td>
</tr>

</table>

<p>
Your registration is now
<strong>confirmed</strong>.
</p>

<p>
Please keep this email for your records.
</p>

<p>
Regards,<br>

<strong>
MMIT Freshers Party 2026
</strong>

<br>

MMIT Kushinagar
</p>

</div>

</body>
</html>
"""

    # ========================================================
    # REJECTED EMAIL
    # ========================================================

    elif status == "REJECTED":

        subject = (
            "MMIT Freshers Party 2026 - "
            "Payment Verification Update"
        )

        body = f"""Hello {display_name},

Your submitted payment for MMIT Freshers Party 2026 could not be verified.

Registration No: {registration_display}
Amount: Rs. {amount_display}
UTR / Transaction ID: {utr or "Not Available"}
Payment Status: REJECTED

Please contact the event administrator and provide the correct payment details if required.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""

        html_content = f"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Payment Update</title>

</head>

<body style="
margin:0;
padding:0;
background:#f4f6f8;
font-family:Arial,Helvetica,sans-serif;
color:#222;
">

<div style="
max-width:650px;
margin:30px auto;
background:#ffffff;
padding:30px;
border-radius:14px;
box-shadow:0 4px 18px rgba(0,0,0,0.08);
">

<h2 style="
margin-top:0;
color:#dc3545;
">
MMIT Freshers Party 2026
</h2>

<p>
Hello
<strong>{html.escape(display_name)}</strong>,
</p>

<p>
Your submitted payment for
<strong>MMIT Freshers Party 2026</strong>
could not be verified.
</p>

<table
width="100%"
cellpadding="12"
style="
border-collapse:collapse;
margin-top:20px;
margin-bottom:20px;
">

<tr>

<td style="border:1px solid #ddd;">
<strong>Registration No.</strong>
</td>

<td style="border:1px solid #ddd;">
{html.escape(registration_display)}
</td>

</tr>

<tr>

<td style="border:1px solid #ddd;">
<strong>Amount</strong>
</td>

<td style="border:1px solid #ddd;">
Rs. {html.escape(amount_display)}
</td>

</tr>

<tr>

<td style="border:1px solid #ddd;">
<strong>UTR / Transaction ID</strong>
</td>

<td style="border:1px solid #ddd;">
{html.escape(str(utr or "Not Available"))}
</td>

</tr>

<tr>

<td style="border:1px solid #ddd;">
<strong>Payment Status</strong>
</td>

<td style="
border:1px solid #ddd;
color:#dc3545;
">

<strong>REJECTED</strong>

</td>

</tr>

</table>

<p>
Please contact the event administrator and provide the correct payment details if required.
</p>

<p>

Regards,<br>

<strong>
MMIT Freshers Party 2026
</strong>

<br>

MMIT Kushinagar

</p>

</div>

</body>

</html>
"""

    else:

        print(
            "Unknown email status:",
            status
        )

        return False

    # ========================================================
    # BREVO API
    # ========================================================

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "accept": "application/json",
        "api-key": brevo_api_key,
        "content-type": "application/json",
    }

    payload = {

        "sender": {
            "name": sender_name,
            "email": sender_email,
        },

        "to": [
            {
                "email": recipient_email,
                "name": student_name,
            }
        ],

        "subject": subject,

        "textContent": body,

        "htmlContent": html_content,

    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(
            "Brevo status:",
            response.status_code
        )

        print(
            "Brevo response:",
            response.text
        )

        if response.status_code == 201:

            print(
                "EMAIL SENT SUCCESSFULLY!"
            )

            return True

        print(
            "EMAIL SEND FAILED"
        )

        return False

    except requests.exceptions.Timeout:

        print("Brevo timeout.")

        return False

    except requests.exceptions.RequestException as e:

        print(
            "Brevo connection error:",
            repr(e)
        )

        return False

    except Exception as e:

        print(
            "Brevo error:",
            repr(e)
        )

        return False
# ============================================================
# CLOUDINARY UPLOAD
# ============================================================

def upload_payment_to_cloudinary(
    file_obj,
    student_id
):

    if not CLOUDINARY_ENABLED:
        return None


    original_name = secure_filename(
        file_obj.filename or "payment.jpg"
    )


    if not original_name:
        original_name = "payment.jpg"


    if not allowed_image(original_name):
        return None


    stored_filename = (
        f"{student_id}_{original_name}"
    )


    base_name = os.path.splitext(
        stored_filename
    )[0]


    try:

        result = cloudinary.uploader.upload(

            file_obj,

            folder="mmit_freshers/payments",

            public_id=base_name,

            resource_type="image",

            overwrite=True,

            unique_filename=False,

        )


        if result.get("secure_url"):

            return stored_filename


        return None


    except Exception as e:

        print(
            "Cloudinary upload error:",
            repr(e)
        )

        return None


# ============================================================
# DELETE CLOUDINARY
# ============================================================

def delete_cloudinary_file(filename):

    if not CLOUDINARY_ENABLED:
        return

    if not filename:
        return


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
            "Cloudinary delete error:",
            repr(e)
        )


# ============================================================
# DELETE LOCAL
# ============================================================

def delete_local_file(filename):

    if not filename:
        return


    safe_filename = secure_filename(
        os.path.basename(filename)
    )


    if not safe_filename:
        return


    path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_filename
    )


    if os.path.isfile(path):

        try:

            os.remove(path)

        except Exception as e:

            print(
                "Local delete error:",
                repr(e)
            )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def create_database():

    conn = get_db_connection()

    cursor = conn.cursor()


    try:

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

                payment_screenshot TEXT,

                participant_type TEXT,

                payment_amount NUMERIC(10,2)

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


        # ====================================================
        # UNIQUE MOBILE
        # ====================================================

        try:

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                unique_student_mobile
                ON students (mobile)
            """)

            conn.commit()

        except Exception as e:

            conn.rollback()

            print(
                "Mobile unique index:",
                repr(e)
            )


        # ====================================================
        # UNIQUE EMAIL
        # ====================================================

        try:

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                unique_student_email
                ON students (LOWER(email))
                WHERE email IS NOT NULL
                AND email <> ''
            """)

            conn.commit()

        except Exception as e:

            conn.rollback()

            print(
                "Email unique index:",
                repr(e)
            )


        # ====================================================
        # UNIQUE UTR
        # ====================================================

        try:

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                unique_student_utr
                ON students (LOWER(utr))
                WHERE utr IS NOT NULL
                AND utr <> ''
            """)

            conn.commit()

        except Exception as e:

            conn.rollback()

            print(
                "UTR unique index:",
                repr(e)
            )


    finally:

        cursor.close()

        conn.close()


try:

    create_database()

    print(
        "Database initialized successfully."
    )

except Exception as e:

    print(
        "Database initialization error:",
        repr(e)
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )


    name = request.form.get(
        "name",
        ""
    ).strip()


    participant_type = request.form.get(
        "participant_type",
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


    roll_number = "N/A"


    # ========================================================
    # BASIC VALIDATION
    # ========================================================

    if not name:

        return (
            "Name is required. "
            "<a href='/register'>Back</a>"
        )


    if not mobile:

        return (
            "Mobile Number is required. "
            "<a href='/register'>Back</a>"
        )


    if not email:

        return (
            "Email is required. "
            "<a href='/register'>Back</a>"
        )


    if not gender:

        return (
            "Gender is required. "
            "<a href='/register'>Back</a>"
        )


    if not is_valid_email(email):

        return (
            "Invalid Email. "
            "<a href='/register'>Back</a>"
        )


    if not mobile.isdigit() or len(mobile) != 10:

        return (
            "Invalid Mobile Number. "
            "<a href='/register'>Back</a>"
        )


    # ========================================================
    # STUDENT
    # ========================================================

    if participant_type == "Student":

        if year not in [
            "1st Year",
            "2nd Year",
            "3rd Year"
        ]:

            return (
                "Please select valid Year. "
                "<a href='/register'>Back</a>"
            )


        if not branch:

            return (
                "Branch is required. "
                "<a href='/register'>Back</a>"
            )


        if year == "1st Year":

            payment_amount = Decimal("199")

        else:

            payment_amount = Decimal("300")


    # ========================================================
    # TEACHER
    # ========================================================

    elif participant_type == "Teacher":

        if not teacher_amount:

            return (
                "Teacher amount is required. "
                "<a href='/register'>Back</a>"
            )


        try:

            payment_amount = Decimal(
                teacher_amount
            )

        except InvalidOperation:

            return (
                "Invalid teacher amount. "
                "<a href='/register'>Back</a>"
            )


        if payment_amount <= 0:

            return (
                "Amount must be greater than 0. "
                "<a href='/register'>Back</a>"
            )


        year = "Teacher"


        if not branch:

            branch = "Teacher"


    else:

        return (
            "Invalid participant type. "
            "<a href='/register'>Back</a>"
        )


    # ========================================================
    # DUPLICATE CHECK
    # ========================================================

    conn = get_db_connection()

    cursor = conn.cursor()


    try:

        cursor.execute("""
            SELECT id
            FROM students
            WHERE mobile = %s
            LIMIT 1
        """, (mobile,))


        existing_mobile = cursor.fetchone()


        cursor.execute("""
            SELECT id
            FROM students
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
        """, (email,))


        existing_email = cursor.fetchone()


    finally:

        cursor.close()

        conn.close()


    if existing_mobile:

        return """

        <h2>Mobile Number Already Registered</h2>

        <p>
        This mobile number is already registered.
        </p>

        <a href="/register">
        Back to Registration
        </a>

        """


    if existing_email:

        return """

        <h2>Email Already Registered</h2>

        <p>
        This email is already registered.
        </p>

        <a href="/register">
        Back to Registration
        </a>

        """


    # ========================================================
    # SESSION
    # ========================================================

    session.permanent = True


    session["pending_registration"] = {

        "name": name,

        "participant_type":
            participant_type,

        "roll_number":
            roll_number,

        "year":
            year,

        "branch":
            branch,

        "mobile":
            mobile,

        "email":
            email,

        "gender":
            gender,

        "payment_amount":
            str(payment_amount),

    }


    # ========================================================
    # PAYMENT PAGE
    # ========================================================

    return render_template(

        "payment.html",

        registration_no="Pending",

        student_name=name,

        amount=payment_amount,

        participant_type=
            participant_type,

        year=year,

    )


# ============================================================
# PAYMENT SUBMIT GET
# ============================================================

@app.route(
    "/payment-submit",
    methods=["GET"]
)
def payment_submit_get():

    pending = session.get(
        "pending_registration"
    )


    if not pending:

        return """

        <h2>Registration Session Expired</h2>

        <a href="/register">
        New Registration
        </a>

        """


    return render_template(

        "payment_submit.html",

        registration_id="",

        student_id="",

        student_name=
            pending.get("name", ""),

        email=
            pending.get("email", ""),

        amount=
            pending.get(
                "payment_amount",
                "0"
            ),

    )


# ============================================================
# OLD URL COMPATIBILITY
# ============================================================

@app.route(
    "/payment-submit/<int:student_id>"
)
def payment_submit_page(student_id):

    return payment_submit_get()


# ============================================================
# SAVE PAYMENT
# ============================================================

@app.route(
    "/payment-submit",
    methods=["POST"]
)
def save_payment():

    pending = session.get(
        "pending_registration"
    )


    if not pending:

        return """

        <h2>Registration Session Expired</h2>

        <a href="/register">
        New Registration
        </a>

        """


    utr = request.form.get(
        "utr",
        ""
    ).strip()


    screenshot = request.files.get(
        "payment_screenshot"
    )


    if not utr:

        return """

        <h2>
        UTR / Transaction ID is required.
        </h2>

        <a href="javascript:history.back()">
        Back
        </a>

        """


    if (
        screenshot is None
        or not screenshot.filename
    ):

        return """

        <h2>
        Payment screenshot is required.
        </h2>

        <a href="javascript:history.back()">
        Back
        </a>

        """


    if not allowed_image(
        screenshot.filename
    ):

        return """

        <h2>
        Invalid Screenshot Format
        </h2>

        <p>
        Only JPG, JPEG, PNG and WEBP are allowed.
        </p>

        <a href="javascript:history.back()">
        Back
        </a>

        """


    name = pending.get(
        "name",
        ""
    )


    participant_type = pending.get(
        "participant_type",
        ""
    )


    roll_number = pending.get(
        "roll_number",
        "N/A"
    )


    year = pending.get(
        "year",
        ""
    )


    branch = pending.get(
        "branch",
        ""
    )


    mobile = pending.get(
        "mobile",
        ""
    )


    email = pending.get(
        "email",
        ""
    )


    gender = pending.get(
        "gender",
        ""
    )


    try:

        payment_amount = Decimal(

            pending.get(
                "payment_amount",
                "0"
            )

        )

    except Exception:

        return "Invalid payment amount."


    if (
        not name
        or not mobile
        or not email
        or not gender
    ):

        return (
            "Registration information incomplete."
        )


    if not participant_type or not branch:

        return (
            "Registration information incomplete."
        )


    # ========================================================
    # DUPLICATE UTR
    # ========================================================

    conn = get_db_connection()

    cursor = conn.cursor()


    try:

        cursor.execute("""
            SELECT id
            FROM students
            WHERE LOWER(utr) = LOWER(%s)
            LIMIT 1
        """, (utr,))


        existing_utr = cursor.fetchone()


    finally:

        cursor.close()

        conn.close()


    if existing_utr:

        return """

        <h2>
        UTR Already Used
        </h2>

        <p>
        This UTR / Transaction ID is already registered.
        </p>

        <a href="/register">
        Back
        </a>

        """


    # ========================================================
    # FILE UPLOAD
    # ========================================================

    temporary_file_id = uuid.uuid4().hex[:12]

    filename = None


    if CLOUDINARY_ENABLED:

        filename = upload_payment_to_cloudinary(

            screenshot,

            temporary_file_id

        )


        if not filename:

            return """

            <h2>
            Screenshot Upload Failed
            </h2>

            <a href="javascript:history.back()">
            Back
            </a>

            """


    else:

        original_name = secure_filename(
            screenshot.filename
        )


        if not original_name:

            return (
                "Invalid screenshot filename."
            )


        filename = (
            f"{temporary_file_id}_"
            f"{original_name}"
        )


        filepath = os.path.join(

            app.config["UPLOAD_FOLDER"],

            filename

        )


        try:

            screenshot.save(filepath)

        except Exception as e:

            print(
                "Local upload error:",
                repr(e)
            )

            return (
                "Payment screenshot could not be saved."
            )


    # ========================================================
    # FINAL INSERT
    # ========================================================

    conn = get_db_connection()

    cursor = conn.cursor()


    try:

        # Final duplicate protection

        cursor.execute("""
            SELECT id
            FROM students
            WHERE mobile = %s
               OR LOWER(email) = LOWER(%s)
               OR LOWER(utr) = LOWER(%s)
            LIMIT 1
        """, (

            mobile,

            email,

            utr,

        ))


        duplicate = cursor.fetchone()


        if duplicate:

            conn.rollback()


            if CLOUDINARY_ENABLED:

                delete_cloudinary_file(
                    filename
                )

            else:

                delete_local_file(
                    filename
                )


            return """

            <h2>
            Duplicate Registration
            </h2>

            <p>
            Mobile, Email या UTR पहले से registered है.
            </p>

            <a href="/register">
            Back
            </a>

            """


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
                utr,
                payment_screenshot,
                participant_type,
                payment_amount
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s
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

            "SUBMITTED",

            utr,

            filename,

            participant_type,

            payment_amount,

        ))


        registration_id = cursor.fetchone()[0]


        conn.commit()


    except psycopg2.errors.UniqueViolation:

        conn.rollback()


        if CLOUDINARY_ENABLED:

            delete_cloudinary_file(
                filename
            )

        else:

            delete_local_file(
                filename
            )


        return """

        <h2>
        Duplicate Registration
        </h2>

        <a href="/register">
        Back
        </a>

        """


    except Exception as e:

        conn.rollback()


        print(
            "INSERT ERROR:",
            repr(e)
        )


        if CLOUDINARY_ENABLED:

            delete_cloudinary_file(
                filename
            )

        else:

            delete_local_file(
                filename
            )


        return """

        <h2>
        Payment Submission Failed
        </h2>

        <p>
        Please try again.
        </p>

        <a href="/register">
        Back
        </a>

        """


    finally:

        cursor.close()

        conn.close()


    # ========================================================
    # CLEAR SESSION
    # ========================================================

    session.pop(
        "pending_registration",
        None
    )


    # ========================================================
    # FORMATTED REGISTRATION NUMBER
    # ========================================================

    formatted_registration_no = (
        format_registration_no(
            registration_id
        )
    )


    # ========================================================
    # SUCCESS PAGE
    # ========================================================

    return f"""

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width,initial-scale=1.0">

<title>
Payment Submitted
</title>

</head>


<body style="
font-family:Arial,Helvetica,sans-serif;
text-align:center;
padding:50px;
background:#f4f6f8;
">


<div style="
max-width:600px;
margin:auto;
background:white;
padding:35px;
border-radius:15px;
box-shadow:0 4px 20px rgba(0,0,0,0.08);
">


<h1 style="
color:#198754;
">

Payment Details Submitted!

</h1>


<h2>

Registration No:

<br>

<span style="
color:#0d6efd;
">

{html.escape(
    formatted_registration_no
)}

</span>

</h2>


<p>
आपका payment record successfully submit हो गया है।
</p>


<p>

Payment Status:

<strong>
SUBMITTED
</strong>

</p>


<p>
Admin payment verify करेगा।
</p>


<br>


<a
href="/"
style="
display:inline-block;
padding:12px 22px;
background:#0d6efd;
color:white;
text-decoration:none;
border-radius:8px;
"
>

Back to Home

</a>


</div>

</body>

</html>

"""


# ============================================================
# PAYMENT STATUS
# ============================================================

@app.route(
    "/payment-status",
    methods=["GET", "POST"]
)
def payment_status():

    if request.method == "GET":

        return render_template(
            "student_status.html"
        )


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
                "UTR / Transaction ID डालना जरूरी है।"
            )

        )


    if not mobile:

        return render_template(

            "student_status.html",

            error=(
                "Mobile Number डालना जरूरी है।"
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
                "UTR / Transaction ID या "
                "Mobile Number गलत है।"
            )

        )

# Student verification successful hone ke baad
# sirf isi student ki receipt allow hogi
    session["receipt_student_id"] = student[0]
    registration_no = format_registration_no(
        student[0]
    )


    return render_template(

        "student_status.html",

        student=student,

        registration_no=registration_no

    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin")
def admin_login_page():

    return render_template(
        "admin_login.html"
    )


@app.route(
    "/admin-login",
    methods=["POST"]
)
def admin_login():

    username = request.form.get(
        "username",
        ""
    ).strip()


    password = request.form.get(
        "password",
        ""
    )


    admin_username = os.environ.get(
        "ADMIN_USERNAME",
        "brijesh"
    ).strip()


    admin_password = os.environ.get(
        "ADMIN_PASSWORD",
        ""
    )


    if not admin_password:

        return """

        <h2>
        Admin password is not configured.
        </h2>

        <p>
        Render Environment Variables में
        ADMIN_PASSWORD set करो.
        </p>

        """


    if (
        username == admin_username
        and password == admin_password
    ):

        session.permanent = True

        session["admin_logged_in"] = True

        return redirect(
            "/admin/dashboard"
        )


    return """

    <h2>
    Invalid Username or Password
    </h2>

    <a href="/admin">
    Try Again
    </a>

    """


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    # ========================================================
    # ADMIN LOGIN CHECK
    # ========================================================

    if not session.get("admin_logged_in"):
        return redirect("/admin")

    conn = None
    cursor = None

    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        # ====================================================
        # GET ALL STUDENTS
        # ====================================================

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

        database_students = cursor.fetchall()

        # ====================================================
        # CONVERT DATABASE DATA TO TEMPLATE ORDER
        #
        # admin_dashboard.html में exact order:
        #
        # 0  = ID
        # 1  = Name
        # 2  = Roll Number
        # 3  = Year
        # 4  = Branch
        # 5  = Mobile
        # 6  = UTR
        # 7  = Payment Status
        # 8  = Screenshot
        # 9  = Participant Type
        # 10 = Payment Amount
        # ====================================================

        students = []

        for row in database_students:

            student_id = row[0]
            name = row[1]
            roll_number = row[2]
            semester = row[3]
            branch = row[4]
            mobile = row[5]
            utr = row[6]
            payment_status = row[7]
            payment_screenshot = row[8]
            participant_type = row[9]
            payment_amount = row[10]

            students.append(
                (
                    student_id,          # 0
                    name,                # 1
                    roll_number,        # 2
                    semester,           # 3 = Year
                    branch,             # 4
                    mobile,             # 5
                    utr,                # 6
                    payment_status,     # 7
                    payment_screenshot, # 8
                    participant_type,   # 9
                    payment_amount      # 10
                )
            )

        # ====================================================
        # TOTAL REGISTRATIONS
        # ====================================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
        """)

        total_registrations = cursor.fetchone()[0]

        # ====================================================
        # PAYMENT SUBMITTED
        # ====================================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
            WHERE payment_status = 'SUBMITTED'
        """)

        payment_submitted = cursor.fetchone()[0]

        # ====================================================
        # PAYMENT VERIFIED
        # ====================================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
            WHERE payment_status = 'VERIFIED'
        """)

        payment_verified = cursor.fetchone()[0]

        # ====================================================
        # PAYMENT REJECTED
        # ====================================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
            WHERE payment_status = 'REJECTED'
        """)

        payment_rejected = cursor.fetchone()[0]

        # ====================================================
        # TOTAL PAYMENT AMOUNT
        #
        # Dashboard में "Total Payment Amount"
        # सभी registrations की amount दिखाएगा.
        # ====================================================

        cursor.execute("""
            SELECT COALESCE(
                SUM(payment_amount),
                0
            )
            FROM students
        """)

        total_collection = cursor.fetchone()[0]

        if total_collection is None:
            total_collection = Decimal("0.00")

        # ====================================================
        # RENDER DASHBOARD
        # ====================================================

        return render_template(
            "admin_dashboard.html",

            students=students,

            total_registrations=total_registrations,

            payment_submitted=payment_submitted,

            payment_verified=payment_verified,

            payment_rejected=payment_rejected,

            total_collection=total_collection,
        )

    # ========================================================
    # ERROR
    # ========================================================

    except Exception as e:

        print(
            "ADMIN DASHBOARD ERROR:",
            repr(e)
        )

        return """
        <h2>
        Admin Dashboard Error
        </h2>

        <p>
        Please try again.
        </p>

        <a href="/admin">
        Back to Admin Login
        </a>
        """

    # ========================================================
    # CLOSE DATABASE
    # ========================================================

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
# ============================================================
# VERIFY PAYMENT
# ============================================================

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
            id,
            name,
            email,
            payment_amount,
            payment_status,
            utr
        FROM students
        WHERE id = %s
    """, (student_id,))


    student = cursor.fetchone()


    if not student:

        cursor.close()

        conn.close()

        return "Student not found."


    database_id = student[0]

    student_name = student[1]

    student_email = student[2]

    payment_amount = student[3]

    payment_status = student[4]

    student_utr = student[5]


    if payment_status != "SUBMITTED":

        cursor.close()

        conn.close()


        return """

        <h2>
        Cannot Verify Payment
        </h2>

        <p>
        Payment SUBMITTED status में नहीं है.
        </p>

        <a href="/admin/dashboard">
        Back
        </a>

        """


    if (
        not student_email
        or not is_valid_email(student_email)
    ):

        cursor.close()

        conn.close()


        return """

        <h2>
        Verification Blocked
        </h2>

        <p>
        Student का valid email मौजूद नहीं है.
        </p>

        <a href="/admin/dashboard">
        Back
        </a>

        """


    cursor.execute("""
        UPDATE students
        SET payment_status = 'VERIFIED'
        WHERE id = %s
        AND payment_status = 'SUBMITTED'
    """, (student_id,))


    if cursor.rowcount != 1:

        conn.rollback()

        cursor.close()

        conn.close()

        return (
            "Payment verification failed."
        )


    conn.commit()

    cursor.close()

    conn.close()


    # ========================================================
    # SEND VERIFIED EMAIL
    # ========================================================

    formatted_registration_no = (
        format_registration_no(
            database_id
        )
    )


    email_result = send_email_notification(

        recipient_email=student_email,

        student_name=student_name,

        registration_id=
            formatted_registration_no,

        amount=payment_amount,

        utr=student_utr,

        status="VERIFIED",

    )


    print(

        "Verified email:",

        "SENT"
        if email_result
        else "FAILED"

    )


    return redirect(
        "/admin/dashboard"
    )


# ============================================================
# REJECT PAYMENT
# ============================================================

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
            id,
            name,
            email,
            payment_amount,
            payment_status,
            utr
        FROM students
        WHERE id = %s
    """, (student_id,))


    student = cursor.fetchone()


    if not student:

        cursor.close()

        conn.close()

        return "Student not found."


    database_id = student[0]

    student_name = student[1]

    student_email = student[2]

    payment_amount = student[3]

    payment_status = student[4]

    student_utr = student[5]


    if payment_status != "SUBMITTED":

        cursor.close()

        conn.close()


        return """

        <h2>
        Cannot Reject Payment
        </h2>

        <a href="/admin/dashboard">
        Back
        </a>

        """


    cursor.execute("""
        UPDATE students
        SET payment_status = 'REJECTED'
        WHERE id = %s
        AND payment_status = 'SUBMITTED'
    """, (student_id,))


    if cursor.rowcount != 1:

        conn.rollback()

        cursor.close()

        conn.close()

        return (
            "Payment rejection failed."
        )


    conn.commit()

    cursor.close()

    conn.close()


    formatted_registration_no = (
        format_registration_no(
            database_id
        )
    )


    email_result = send_email_notification(

        recipient_email=student_email,

        student_name=student_name,

        registration_id=
            formatted_registration_no,

        amount=payment_amount,

        utr=student_utr,

        status="REJECTED",

    )


    print(

        "Rejected email:",

        "SENT"
        if email_result
        else "FAILED"

    )


    return redirect(
        "/admin/dashboard"
    )


# ============================================================
# DELETE ONE
# ============================================================

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
            SELECT payment_screenshot
            FROM students
            WHERE id = %s
        """, (student_id,))


        student = cursor.fetchone()


        if not student:

            return "Student not found."


        screenshot = student[0]


        cursor.execute("""
            DELETE FROM students
            WHERE id = %s
        """, (student_id,))


        conn.commit()


        if screenshot:

            delete_local_file(
                screenshot
            )

            delete_cloudinary_file(
                screenshot
            )


        return redirect(
            "/admin/dashboard"
        )


    except Exception as e:

        if conn:

            conn.rollback()


        print(
            "Delete error:",
            repr(e)
        )


        return "Delete failed."


    finally:

        if cursor:

            cursor.close()


        if conn:

            conn.close()


# ============================================================
# DELETE ALL
# ============================================================

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


        for row in screenshots:

            filename = row[0]


            if filename:

                delete_local_file(
                    filename
                )

                delete_cloudinary_file(
                    filename
                )


        return redirect(
            "/admin/dashboard"
        )


    except Exception as e:

        if conn:

            conn.rollback()


        print(
            "Delete all error:",
            repr(e)
        )


        return "Delete All Failed."


    finally:

        if cursor:

            cursor.close()


        if conn:

            conn.close()


# ============================================================
# ADMIN RECEIPT
# ============================================================

@app.route(
    "/admin/receipt/<int:student_id>"
)
def payment_receipt(student_id):

    if not session.get(
        "admin_logged_in"
    ):

        return redirect("/admin")


    return get_receipt(
        student_id,
        "/admin/dashboard"
    )


# ============================================================
# STUDENT RECEIPT
# ============================================================

@app.route(
    "/student/receipt/<int:student_id>"
)
def student_receipt(student_id):

    allowed_student_id = session.get(
        "receipt_student_id"
    )

    if allowed_student_id != student_id:
        return """
        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>Access Denied</h2>

            <p>
            यह receipt आपके लिए उपलब्ध नहीं है।
            </p>

            <a href="/payment-status">
            Payment Status पर जाएँ
            </a>

        </div>
        """, 403

    return get_receipt(
        student_id,
        "/payment-status"
    )

# ============================================================
# RECEIPT HELPER
# ============================================================

def get_receipt(
    student_id,
    back_url
):

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
    """, (student_id,))


    student = cursor.fetchone()


    cursor.close()

    conn.close()


    if student is None:

        return "Student not found."


    if student[7] != "VERIFIED":

        return f"""

        <div style="
            font-family:Arial;
            text-align:center;
            padding:50px;
        ">

            <h2>
            Payment Not Verified
            </h2>

            <p>
            Receipt केवल verified payment के बाद
            generate की जा सकती है।
            </p>

            <a href="{back_url}">
            Back
            </a>

        </div>

        """


    # ========================================================
    # FORMATTED REGISTRATION NUMBER
    # ========================================================

    registration_no = (
        format_registration_no(
            student[0]
        )
    )


    return render_template(

        "receipt.html",

        student=student,

        registration_no=
            registration_no

    )


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )

    return redirect("/admin")


# ============================================================
# RUN
# ============================================================

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