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
import psycopg2
import requests
import html
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from werkzeug.utils import secure_filename


# ============================================================
# OPTIONAL CLOUDINARY IMPORT
# ============================================================

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
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


# ============================================================
# SESSION SETTINGS
# ============================================================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

if os.environ.get("RENDER"):
    app.config["SESSION_COOKIE_SECURE"] = True

app.permanent_session_lifetime = timedelta(
    minutes=60
)


# ============================================================
# WEBSITE BASE URL
# ============================================================

APP_BASE_URL = os.environ.get(
    "APP_BASE_URL",
    ""
).strip().rstrip("/")


def get_base_url():
    """
    Returns public website base URL.

    Priority:
    1. APP_BASE_URL environment variable
    2. Current Flask request URL
    """

    if APP_BASE_URL:
        return APP_BASE_URL

    try:
        return request.url_root.rstrip("/")
    except Exception:
        return ""


# ============================================================
# REGISTRATION NUMBER
# ============================================================
# Database ID 3 will be displayed as:
# MMIT-2026-0003
#
# Database ID 15 will be displayed as:
# MMIT-2026-0015
# ============================================================

def format_registration_no(registration_id):

    try:
        return f"MMIT-2026-{int(registration_id):04d}"

    except (TypeError, ValueError):

        return str(
            registration_id or ""
        )


# ============================================================
# CLOUDINARY CONFIGURATION
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


print("=" * 50, flush=True)
print("CLOUDINARY CONFIGURATION", flush=True)

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

print("=" * 50, flush=True)


# ============================================================
# ALLOWED IMAGE EXTENSIONS
# ============================================================

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


def allowed_image(filename):

    if not filename:
        return False

    filename = filename.lower().strip()

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1]

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

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return bool(
        re.match(
            pattern,
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

    # --------------------------------------------------------
    # CLOUDINARY
    # --------------------------------------------------------

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

            return redirect(
                url,
                code=302
            )

        except Exception as e:

            print(
                "Cloudinary image redirect error:",
                repr(e),
                flush=True
            )

    # --------------------------------------------------------
    # LOCAL FALLBACK
    # --------------------------------------------------------

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

    print("=" * 50, flush=True)
    print("BREVO EMAIL START", flush=True)

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
        "UTR:",
        utr,
        flush=True
    )

    print(
        "Status:",
        status,
        flush=True
    )

    # --------------------------------------------------------
    # EMAIL CHECK
    # --------------------------------------------------------

    if not recipient_email:

        print(
            "Student email is EMPTY.",
            flush=True
        )

        return False

    recipient_email = recipient_email.strip()

    if not recipient_email:
        return False

    if not is_valid_email(recipient_email):

        print(
            "Student email is invalid.",
            flush=True
        )

        return False

    # --------------------------------------------------------
    # BREVO ENVIRONMENT VARIABLES
    # --------------------------------------------------------

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

    if not brevo_api_key:

        print(
            "BREVO_API_KEY is missing.",
            flush=True
        )

        return False

    if not brevo_sender_email:

        print(
            "BREVO_SENDER_EMAIL is missing.",
            flush=True
        )

        return False

    if not is_valid_email(brevo_sender_email):

        print(
            "BREVO_SENDER_EMAIL is invalid.",
            flush=True
        )

        return False

    # --------------------------------------------------------
    # SAFE HTML VALUES
    # --------------------------------------------------------

    safe_student_name = html.escape(
        str(student_name or "")
    )

    safe_registration_id = html.escape(
        str(registration_id or "")
    )

    safe_utr = html.escape(
        str(utr or "Not Available")
    )

    try:

        formatted_amount = Decimal(
            str(amount or "0")
        ).quantize(
            Decimal("0.01")
        )

    except Exception:

        formatted_amount = Decimal("0.00")

    safe_amount = html.escape(
        f"{formatted_amount:.2f}"
    )

    base_url = get_base_url()

    # --------------------------------------------------------
    # LOGO
    # --------------------------------------------------------

    logo_url = ""

    if base_url:

        logo_url = (
            f"{base_url}/static/image/college.jpg"
        )

    # ========================================================
    # VERIFIED EMAIL
    # ========================================================

    if status == "VERIFIED":

        subject = (
            "MMIT Freshers Party 2026 - "
            "Payment Verified Successfully"
        )

        # ----------------------------------------------------
        # CANONICAL VERIFIED EMAIL FORMAT
        # ----------------------------------------------------
        # Mobile और laptop दोनों पर बिल्कुल यही information
        # भेजी जाएगी.
        #
        # Example:
        # Hello Rajnish,
        # Your payment for MMIT Freshers Party 2026 has been
        # successfully verified.
        # Registration No: 6
        # Amount: ₹199.00
        # Payment Status: VERIFIED
        # ----------------------------------------------------

        raw_name = str(student_name or "").strip()

        # केवल पहला नाम दिखाएँ और सही capitalization रखें.
        # "RAJNISH PRASAD" -> "Rajnish"
        # "rajnish prasad" -> "Rajnish"
        first_name = raw_name.split()[0] if raw_name else "Student"
        display_name = first_name[:1].upper() + first_name[1:].lower()

        # VERIFIED email में database का actual numeric ID ही
        # Registration No के रूप में दिखाया जाएगा.
        registration_display = str(registration_id or "").strip()

        try:
            registration_display = str(
                int(registration_display)
            )
        except (TypeError, ValueError):
            # अगर formatted ID आया हो जैसे MMIT-2026-0006,
            # तो केवल 6 दिखाएँ.
            try:
                registration_display = str(
                    int(registration_display.split("-")[-1])
                )
            except (TypeError, ValueError):
                pass

        # Amount हमेशा ₹199.00 जैसे format में जाएगा.
        amount_display = f"{formatted_amount:.2f}"

        # ----------------------------------------------------
        # SAME CONTENT FOR HTML + PLAIN TEXT
        # ----------------------------------------------------
        # इससे mobile/laptop या अलग email client में template
        # बदलने की समस्या नहीं होगी.
        # ----------------------------------------------------

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Verified</title>
</head>
<body style="
    margin:0;
    padding:0;
    background:#ffffff;
    font-family:Arial,Helvetica,sans-serif;
    color:#222222;
">
    <div style="
        max-width:650px;
        margin:0 auto;
        padding:30px 20px;
        line-height:1.7;
        font-size:15px;
    ">
        <p>Hello <strong>{html.escape(display_name)}</strong>,</p>

        <p>
            Your payment for MMIT Freshers Party 2026 has been
            successfully verified.
        </p>

        <p>
            <strong>Registration No:</strong> {html.escape(registration_display)}<br>
            <strong>Amount:</strong> ₹{html.escape(amount_display)}<br>
            <strong>Payment Status:</strong> VERIFIED
        </p>

        <p>
            Your registration is now confirmed.
        </p>

        <p>
            Please keep this email for your records.
        </p>

        <p>
            Regards,<br>
            <strong>MMIT Freshers Party 2026</strong><br>
            MMIT Kushinagar
        </p>
    </div>
</body>
</html>
"""

        body = f"""Hello {display_name},

Your payment for MMIT Freshers Party 2026 has been successfully verified.

Registration No: {registration_display}
Amount: ₹{amount_display}
Payment Status: VERIFIED

Your registration is now confirmed.

Please keep this email for your records.

Regards,
MMIT Freshers Party 2026
MMIT Kushinagar
"""

    # ========================================================
    # REJECTED EMAIL
    # ========================================================

    elif status == "REJECTED":

        subject = (
            "MMIT Freshers Party 2026 - "
            "Payment Verification Update"
        )

        html_content = f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>MMIT Payment Update</title>

</head>

<body
    style="
        margin:0;
        padding:0;
        background:#f4f6f8;
        font-family:Arial,Helvetica,sans-serif;
        color:#222222;
    "
>

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="background:#f4f6f8;padding:30px 10px;"
>

<tr>

<td align="center">

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="
        max-width:650px;
        background:#ffffff;
        border-radius:12px;
        overflow:hidden;
        box-shadow:0 3px 15px rgba(0,0,0,0.08);
    "
>

<tr>

<td
    align="center"
    style="
        background:#dc3545;
        padding:28px 20px;
        color:#ffffff;
    "
>

<div
    style="
        font-size:24px;
        font-weight:bold;
    "
>
MMIT Freshers Party 2026
</div>

<div
    style="
        font-size:14px;
        margin-top:6px;
    "
>
MMIT Kushinagar
</div>

</td>

</tr>


<tr>

<td style="padding:30px 28px;">

<h2
    style="
        margin:0 0 15px 0;
        color:#dc3545;
    "
>
Payment Verification Update
</h2>

<p>
Hello <strong>{safe_student_name}</strong>,
</p>

<p
    style="
        line-height:1.7;
        color:#555555;
    "
>
Your submitted payment for
<strong>MMIT Freshers Party 2026</strong>
could not be verified.
</p>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    style="
        margin-top:20px;
        border:1px solid #e1e5e9;
        border-radius:8px;
    "
>

<tr>

<td
    style="
        padding:12px;
        font-weight:bold;
        background:#f8f9fa;
    "
>
Registration No.
</td>

<td
    style="
        padding:12px;
        background:#f8f9fa;
        font-weight:bold;
        color:#dc3545;
    "
>
{safe_registration_id}
</td>

</tr>


<tr>

<td
    style="
        padding:12px;
        border-top:1px solid #e1e5e9;
        font-weight:bold;
    "
>
Amount
</td>

<td
    style="
        padding:12px;
        border-top:1px solid #e1e5e9;
    "
>
₹{safe_amount}
</td>

</tr>


<tr>

<td
    style="
        padding:12px;
        background:#f8f9fa;
        border-top:1px solid #e1e5e9;
        font-weight:bold;
    "
>
UTR / Transaction ID
</td>

<td
    style="
        padding:12px;
        background:#f8f9fa;
        border-top:1px solid #e1e5e9;
        word-break:break-all;
    "
>
{safe_utr}
</td>

</tr>


<tr>

<td
    style="
        padding:12px;
        border-top:1px solid #e1e5e9;
        font-weight:bold;
    "
>
Payment Status
</td>

<td
    style="
        padding:12px;
        border-top:1px solid #e1e5e9;
        color:#dc3545;
        font-weight:bold;
    "
>
REJECTED
</td>

</tr>

</table>


<p
    style="
        margin-top:25px;
        line-height:1.7;
        color:#555555;
    "
>
Please contact the event administrator and
provide the correct payment details if required.
</p>


<p
    style="
        margin-top:25px;
        line-height:1.6;
    "
>
Regards,<br>

<strong>
MMIT Freshers Party 2026
</strong><br>

MMIT Kushinagar

</p>

</td>

</tr>


<tr>

<td
    align="center"
    style="
        background:#f8f9fa;
        padding:20px;
        color:#777777;
        font-size:12px;
    "
>

This is an automated email from MMIT Freshers Party 2026.

</td>

</tr>

</table>

</td>

</tr>

</table>

</body>

</html>
"""

        body = f"""
Hello {student_name},

Your submitted payment for MMIT Freshers Party 2026 could not be verified.

Registration No: {registration_id}

Amount: ₹{formatted_amount:.2f}

UTR / Transaction ID: {utr}

Payment Status: REJECTED

Please contact the event administrator and provide the correct payment details if required.

Regards,

MMIT Freshers Party 2026

MMIT Kushinagar
"""

    else:

        print(
            "Invalid email status:",
            status,
            flush=True
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
            "Brevo HTTP Status:",
            response.status_code,
            flush=True
        )

        print(
            "BREVO RESPONSE:",
            response.text,
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
                "EMAIL SENT SUCCESSFULLY!",
                flush=True
            )

            return True

        print(
            "BREVO EMAIL FAILED:",
            response.text,
            flush=True
        )

        return False

    except requests.exceptions.Timeout:

        print(
            "BREVO API TIMEOUT",
            flush=True
        )

        return False

    except requests.exceptions.RequestException as e:

        print(
            "BREVO API CONNECTION ERROR:",
            repr(e),
            flush=True
        )

        return False

    except Exception as e:

        print(
            "BREVO EMAIL ERROR:",
            repr(e),
            flush=True
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
            "Cloudinary upload failed:",
            repr(e),
            flush=True
        )

        return None


# ============================================================
# DELETE CLOUDINARY IMAGE
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
            f"mmit_freshers/payments/{base_filename}"
        )

        cloudinary.uploader.destroy(
            public_id,
            resource_type="image"
        )

        print(
            "Cloudinary file deleted:",
            public_id,
            flush=True
        )

    except Exception as e:

        print(
            "Cloudinary delete error:",
            repr(e),
            flush=True
        )


# ============================================================
# DELETE LOCAL IMAGE
# ============================================================

def delete_local_file(filename):

    if not filename:
        return

    safe_filename = secure_filename(
        os.path.basename(filename)
    )

    if not safe_filename:
        return

    local_file = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_filename
    )

    if os.path.isfile(local_file):

        try:

            os.remove(local_file)

            print(
                "Local file deleted:",
                local_file,
                flush=True
            )

        except Exception as e:

            print(
                "Local file delete error:",
                repr(e),
                flush=True
            )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def create_database():

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # MAIN TABLE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # NEW COLUMNS
        # ----------------------------------------------------

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN IF NOT EXISTS participant_type TEXT
        """)

        cursor.execute("""
            ALTER TABLE students
            ADD COLUMN IF NOT EXISTS payment_amount NUMERIC(10,2)
        """)

        conn.commit()

        # ----------------------------------------------------
        # UNIQUE MOBILE
        # ----------------------------------------------------

        try:

            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                unique_student_mobile
                ON students (mobile)
            """)

            conn.commit()

            print(
                "Unique mobile protection enabled.",
                flush=True
            )

        except Exception as e:

            conn.rollback()

            print(
                "Mobile unique index could not be created:",
                repr(e),
                flush=True
            )

        # ----------------------------------------------------
        # UNIQUE EMAIL
        # ----------------------------------------------------

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
                "Unique email protection enabled.",
                flush=True
            )

        except Exception as e:

            conn.rollback()

            print(
                "Email unique index could not be created:",
                repr(e),
                flush=True
            )

        # ----------------------------------------------------
        # UNIQUE UTR
        # ----------------------------------------------------

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
                "Unique UTR protection enabled.",
                flush=True
            )

        except Exception as e:

            conn.rollback()

            print(
                "UTR unique index could not be created:",
                repr(e),
                flush=True
            )

    finally:

        cursor.close()
        conn.close()


# ============================================================
# DATABASE STARTUP
# ============================================================

try:

    create_database()

    print(
        "Database initialized successfully.",
        flush=True
    )

except Exception as e:

    print(
        "Database initialization error:",
        repr(e),
        flush=True
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
# REGISTRATION
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        # ----------------------------------------------------
        # FORM DATA
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        if not name:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Name is required.</h2>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # MOBILE
        # ----------------------------------------------------

        if not mobile:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Mobile Number is required.</h2>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # EMAIL
        # ----------------------------------------------------

        if not email:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Email is required.</h2>

                <p>
                    Payment करने के लिए valid email देना जरूरी है।
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # GENDER
        # ----------------------------------------------------

        if not gender:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Gender is required.</h2>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # EMAIL FORMAT
        # ----------------------------------------------------

        if not is_valid_email(email):

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Invalid Email Address</h2>

                <p>
                    कृपया valid email address डालें।
                </p>

                <p>
                    Example: student@gmail.com
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # MOBILE FORMAT
        # ----------------------------------------------------

        if not mobile.isdigit() or len(mobile) != 10:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Invalid Mobile Number</h2>

                <p>
                    कृपया 10 digit valid mobile number डालें।
                </p>

                <a href="/register">
                    Back
                </a>

            </div>
            """

        # ----------------------------------------------------
        # PARTICIPANT TYPE
        # ----------------------------------------------------

        if participant_type == "Student":

            if year not in [
                "1st Year",
                "2nd Year",
                "3rd Year"
            ]:

                return (
                    "Please select a valid Year. "
                    "<a href='/register'>Back</a>"
                )

            payment_amount = (
                Decimal("199")
                if year == "1st Year"
                else Decimal("300")
            )

            if not branch:

                return (
                    "Branch is required. "
                    "<a href='/register'>Back</a>"
                )

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

        # ----------------------------------------------------
        # DATABASE DUPLICATE CHECK
        # ----------------------------------------------------

        conn = get_db_connection()
        cursor = conn.cursor()

        try:

            cursor.execute("""
                SELECT id, name
                FROM students
                WHERE mobile = %s
                LIMIT 1
            """, (mobile,))

            existing_mobile = cursor.fetchone()

            cursor.execute("""
                SELECT id, name
                FROM students
                WHERE LOWER(email) = LOWER(%s)
                LIMIT 1
            """, (email,))

            existing_email = cursor.fetchone()

        finally:

            cursor.close()
            conn.close()

        # ----------------------------------------------------
        # DUPLICATE MOBILE
        # ----------------------------------------------------

        if existing_mobile:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Mobile Number Already Registered</h2>

                <p>
                    यह mobile number पहले से registration
                    में इस्तेमाल हो चुका है।
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # DUPLICATE EMAIL
        # ----------------------------------------------------

        if existing_email:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Email Already Registered</h2>

                <p>
                    यह email पहले से registration
                    में इस्तेमाल हो चुका है।
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # SESSION
        # ----------------------------------------------------

        session.permanent = True

        session["pending_registration"] = {

            "name": name,

            "participant_type": participant_type,

            "roll_number": roll_number,

            "year": year,

            "branch": branch,

            "mobile": mobile,

            "email": email,

            "gender": gender,

            "payment_amount": str(payment_amount),

        }

        # ----------------------------------------------------
        # PAYMENT PAGE
        # ----------------------------------------------------

        return render_template(
            "payment.html",
            registration_no="Pending",
            student_name=name,
            amount=payment_amount,
            participant_type=participant_type,
            year=year,
        )

    return render_template(
        "register.html"
    )


# ============================================================
# PAYMENT SUBMIT PAGE
# ============================================================

@app.route(
    "/payment-submit/<int:student_id>"
)
def payment_submit_page(student_id):

    pending = session.get(
        "pending_registration"
    )

    if not pending:

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Registration Session Expired</h2>

            <p>
                आपकी registration information उपलब्ध नहीं है।
            </p>

            <a href="/register">
                New Registration
            </a>

        </div>
        """

    return render_template(
        "payment_submit.html",

        registration_id="",

        student_id="",

        student_name=pending.get(
            "name",
            ""
        ),

        email=pending.get(
            "email",
            ""
        ),

        amount=pending.get(
            "payment_amount",
            "0"
        ),
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
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Registration Session Expired</h2>

            <p>
                कृपया पहले registration complete करें।
            </p>

            <a href="/register">
                New Registration
            </a>

        </div>
        """

    return render_template(
        "payment_submit.html",

        registration_id="",

        student_id="",

        student_name=pending.get(
            "name",
            ""
        ),

        email=pending.get(
            "email",
            ""
        ),

        amount=pending.get(
            "payment_amount",
            "0"
        ),
    )


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
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Registration Session Expired</h2>

            <p>
                Registration information नहीं मिली।
            </p>

            <a href="/register">
                New Registration
            </a>

        </div>
        """

    # --------------------------------------------------------
    # PAYMENT DATA
    # --------------------------------------------------------

    utr = request.form.get(
        "utr",
        ""
    ).strip()

    screenshot = request.files.get(
        "payment_screenshot"
    )

    # --------------------------------------------------------
    # UTR
    # --------------------------------------------------------

    if not utr:

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>UTR / Transaction ID is required.</h2>

            <a href="javascript:history.back()">
                Back
            </a>

        </div>
        """

    # --------------------------------------------------------
    # SCREENSHOT
    # --------------------------------------------------------

    if (
        screenshot is None
        or screenshot.filename == ""
    ):

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Payment screenshot is required.</h2>

            <a href="javascript:history.back()">
                Back
            </a>

        </div>
        """

    if not allowed_image(
        screenshot.filename
    ):

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Invalid Screenshot Format</h2>

            <p>
                Only JPG, JPEG, PNG and WEBP images are allowed.
            </p>

            <a href="javascript:history.back()">
                Back
            </a>

        </div>
        """

    # --------------------------------------------------------
    # SESSION DATA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not name:
        return "Registration name missing."

    if not mobile:
        return "Mobile number missing."

    if not email:
        return "Email missing."

    if not gender:
        return "Gender missing."

    if not participant_type:
        return "Participant type missing."

    if not branch:
        return "Branch missing."

    if not is_valid_email(email):

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Invalid Email</h2>

            <p>
                Registration का email valid नहीं है।
            </p>

            <a href="/register">
                New Registration
            </a>

        </div>
        """

    # --------------------------------------------------------
    # DATABASE DUPLICATE CHECK
    # --------------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT id, name
            FROM students
            WHERE mobile = %s
            LIMIT 1
        """, (mobile,))

        existing_mobile = cursor.fetchone()

        if existing_mobile:

            session.pop(
                "pending_registration",
                None
            )

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Mobile Number Already Registered</h2>

                <p>
                    यह mobile number पहले से registered है।
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        cursor.execute("""
            SELECT id, name
            FROM students
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
        """, (email,))

        existing_email = cursor.fetchone()

        if existing_email:

            session.pop(
                "pending_registration",
                None
            )

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Email Already Registered</h2>

                <p>
                    यह email पहले से registered है।
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # UTR DUPLICATE
        # ----------------------------------------------------

        cursor.execute("""
            SELECT id, name
            FROM students
            WHERE LOWER(utr) = LOWER(%s)
            LIMIT 1
        """, (utr,))

        existing_utr = cursor.fetchone()

        if existing_utr:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>UTR Already Used</h2>

                <p>
                    यह UTR / Transaction ID पहले से इस्तेमाल हो चुका है।
                </p>

                <a href="javascript:history.back()">
                    Back
                </a>

            </div>
            """

    finally:

        cursor.close()
        conn.close()

    # --------------------------------------------------------
    # TEMPORARY FILE ID
    # --------------------------------------------------------

    temporary_file_id = uuid.uuid4().hex[:12]

    filename = None

    # --------------------------------------------------------
    # CLOUDINARY UPLOAD
    # --------------------------------------------------------

    if CLOUDINARY_ENABLED:

        filename = upload_payment_to_cloudinary(
            screenshot,
            temporary_file_id
        )

        if not filename:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Screenshot Upload Failed</h2>

                <p>
                    Payment screenshot upload नहीं हो पाया।
                </p>

                <a href="javascript:history.back()">
                    Back
                </a>

            </div>
            """

    # --------------------------------------------------------
    # LOCAL UPLOAD
    # --------------------------------------------------------

    else:

        original_name = secure_filename(
            screenshot.filename
        )

        if not original_name:

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Invalid screenshot filename.</h2>

                <a href="javascript:history.back()">
                    Back
                </a>

            </div>
            """

        filename = (
            f"{temporary_file_id}_{original_name}"
        )

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        try:

            screenshot.save(
                filepath
            )

            print(
                "Screenshot saved locally:",
                filepath,
                flush=True
            )

        except Exception as e:

            print(
                "Local screenshot save error:",
                repr(e),
                flush=True
            )

            return (
                "Payment screenshot could not "
                "be saved. Please try again."
            )

    # --------------------------------------------------------
    # FINAL DATABASE INSERT
    # --------------------------------------------------------

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # FINAL DUPLICATE CHECK
        # ----------------------------------------------------

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
                delete_cloudinary_file(filename)
            else:
                delete_local_file(filename)

            return """
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>Duplicate Registration</h2>

                <p>
                    Mobile, Email या UTR पहले से registered है।
                </p>

                <a href="/register">
                    Back to Registration
                </a>

            </div>
            """

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

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
                %s,
                %s,
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
            "SUBMITTED",
            utr,
            filename,
            participant_type,
            payment_amount,
        ))

        registration_id = cursor.fetchone()[0]

        conn.commit()

        formatted_registration_no = format_registration_no(
            registration_id
        )

        print(
            "Registration + payment saved.",
            "Registration ID:",
            registration_id,
            flush=True
        )

        print(
            "Display Registration No:",
            formatted_registration_no,
            flush=True
        )

    except psycopg2.errors.UniqueViolation:

        conn.rollback()

        if CLOUDINARY_ENABLED:
            delete_cloudinary_file(filename)
        else:
            delete_local_file(filename)

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Duplicate Registration</h2>

            <p>
                Mobile, Email या UTR पहले से registered है।
            </p>

            <a href="/register">
                Back to Registration
            </a>

        </div>
        """

    except Exception as e:

        conn.rollback()

        print(
            "Registration INSERT error:",
            repr(e),
            flush=True
        )

        if CLOUDINARY_ENABLED:
            delete_cloudinary_file(filename)
        else:
            delete_local_file(filename)

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>Payment Submission Failed</h2>

            <p>
                Payment details database में save नहीं हो सके।
            </p>

            <p>
                कृपया दोबारा कोशिश करें।
            </p>

            <a href="/register">
                Back to Registration
            </a>

        </div>
        """

    finally:

        cursor.close()
        conn.close()

    # --------------------------------------------------------
    # REMOVE SESSION
    # --------------------------------------------------------

    session.pop(
        "pending_registration",
        None
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    return f"""
    <div style="font-family:Arial;text-align:center;padding:50px;">

        <h1>
            Payment Details Submitted!
        </h1>

        <h2>
            Registration No: {formatted_registration_no}
        </h2>

        <p>
            आपका payment record successfully submit हो गया है।
        </p>

        <p>
            Payment Status:
            <strong>SUBMITTED</strong>
        </p>

        <p>
            Admin payment verify करेगा।
        </p>

        <br>

        <a href="/">
            Back to Home
        </a>

    </div>
    """


# ============================================================
# STUDENT PAYMENT STATUS
# ============================================================

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
                    "UTR / Transaction ID "
                    "डालना जरूरी है।"
                )
            )

        if not mobile:

            return render_template(
                "student_status.html",
                error=(
                    "Mobile Number "
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
                    "UTR / Transaction ID "
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


# ============================================================
# ADMIN LOGIN PAGE
# ============================================================

@app.route("/admin")
def admin_login_page():

    return render_template(
        "admin_login.html"
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

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
        "ADMIN_PASSWORD"
    )

    if not admin_password:

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Admin password is not configured.
            </h2>

            <p>
                Please set ADMIN_PASSWORD in Render
                Environment Variables.
            </p>

        </div>
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
    <div style="font-family:Arial;text-align:center;padding:50px;">

        <h2>
            Invalid Username or Password
        </h2>

        <a href="/admin">
            Try Again
        </a>

    </div>
    """


# ============================================================
# ADMIN DASHBOARD
# ============================================================

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
            name,
            email,
            payment_amount,
            payment_status,
            utr
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
    student_utr = student[4]

    # --------------------------------------------------------
    # ONLY SUBMITTED
    # --------------------------------------------------------

    if payment_status != "SUBMITTED":

        cursor.close()
        conn.close()

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Cannot Verify Payment
            </h2>

            <p>
                यह payment अभी SUBMITTED status में नहीं है।
            </p>

            <a href="/admin/dashboard">
                Back to Dashboard
            </a>

        </div>
        """

    # --------------------------------------------------------
    # EMAIL CHECK
    # --------------------------------------------------------

    if (
        not student_email
        or not is_valid_email(student_email)
    ):

        cursor.close()
        conn.close()

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Verification Blocked
            </h2>

            <p>
                Student का valid email मौजूद नहीं है।
            </p>

            <a href="/admin/dashboard">
                Back to Dashboard
            </a>

        </div>
        """

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

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

        return "Payment verification failed."

    conn.commit()

    cursor.close()
    conn.close()

    # --------------------------------------------------------
    # FORMATTED REGISTRATION NUMBER
    # --------------------------------------------------------

    formatted_registration_no = format_registration_no(
        student_id
    )

    # --------------------------------------------------------
    # BREVO
    # --------------------------------------------------------

    email_result = send_email_notification(

        recipient_email=student_email,

        student_name=student_name,

        # VERIFIED email में केवल actual numeric registration ID भेजें.
        # इससे mobile और laptop दोनों पर एक ही format आएगा.
        registration_id=student_id,

        amount=payment_amount,

        utr=student_utr,

        status="VERIFIED",
    )

    if email_result:

        print(
            "Verified email sent.",
            flush=True
        )

    else:

        print(
            "Payment verified, but email was NOT sent.",
            flush=True
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
            name,
            email,
            payment_amount,
            payment_status,
            utr
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
    student_utr = student[4]

    if payment_status != "SUBMITTED":

        cursor.close()
        conn.close()

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Cannot Reject Payment
            </h2>

            <p>
                यह payment SUBMITTED status में नहीं है।
            </p>

            <a href="/admin/dashboard">
                Back to Dashboard
            </a>

        </div>
        """

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

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

        return "Payment rejection failed."

    conn.commit()

    cursor.close()
    conn.close()

    # --------------------------------------------------------
    # FORMATTED REGISTRATION NUMBER
    # --------------------------------------------------------

    formatted_registration_no = format_registration_no(
        student_id
    )

    # --------------------------------------------------------
    # BREVO
    # --------------------------------------------------------

    email_result = send_email_notification(

        recipient_email=student_email,

        student_name=student_name,

        registration_id=formatted_registration_no,

        amount=payment_amount,

        utr=student_utr,

        status="REJECTED",
    )

    if email_result:

        print(
            "Rejected email sent.",
            flush=True
        )

    else:

        print(
            "Payment rejected, but email was NOT sent.",
            flush=True
        )

    return redirect(
        "/admin/dashboard"
    )


# ============================================================
# ADMIN DELETE ONE
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
            <div style="font-family:Arial;text-align:center;padding:50px;">

                <h2>
                    Student Not Found
                </h2>

                <a href="/admin/dashboard">
                    Back to Dashboard
                </a>

            </div>
            """

        screenshot_filename = student[2]

        # ----------------------------------------------------
        # DELETE DATABASE
        # ----------------------------------------------------

        cursor.execute("""
            DELETE FROM students
            WHERE id = %s
        """, (
            student_id,
        ))

        conn.commit()

        # ----------------------------------------------------
        # LOCAL
        # ----------------------------------------------------

        if screenshot_filename:

            delete_local_file(
                screenshot_filename
            )

        # ----------------------------------------------------
        # CLOUDINARY
        # ----------------------------------------------------

        if (
            CLOUDINARY_ENABLED
            and screenshot_filename
        ):

            delete_cloudinary_file(
                screenshot_filename
            )

        return redirect(
            "/admin/dashboard"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "DELETE STUDENT ERROR:",
            repr(e),
            flush=True
        )

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Delete Failed
            </h2>

            <a href="/admin/dashboard">
                Back to Dashboard
            </a>

        </div>
        """

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# ADMIN DELETE ALL
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

        # ----------------------------------------------------
        # DELETE ALL
        # ----------------------------------------------------

        cursor.execute("""
            DELETE FROM students
        """)

        # ----------------------------------------------------
        # RESET ID
        # ----------------------------------------------------

        cursor.execute("""
            ALTER SEQUENCE students_id_seq
            RESTART WITH 1
        """)

        conn.commit()

        # ----------------------------------------------------
        # LOCAL FILES
        # ----------------------------------------------------

        for screenshot in screenshots:

            filename = screenshot[0]

            if not filename:
                continue

            delete_local_file(
                filename
            )

        # ----------------------------------------------------
        # CLOUDINARY FILES
        # ----------------------------------------------------

        if CLOUDINARY_ENABLED:

            for screenshot in screenshots:

                filename = screenshot[0]

                if not filename:
                    continue

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
            "DELETE ALL ERROR:",
            repr(e),
            flush=True
        )

        return """
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Delete All Failed
            </h2>

            <a href="/admin/dashboard">
                Back to Dashboard
            </a>

        </div>
        """

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ============================================================
# ADMIN PAYMENT RECEIPT
# ============================================================

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
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Payment Not Verified
            </h2>

            <p>
                Receipt केवल verified payment
                के बाद generate की जा सकती है।
            </p>

            <a href="/admin/dashboard">
                Back to Dashboard
            </a>

        </div>
        """

    # --------------------------------------------------------
    # FORMATTED REGISTRATION NUMBER
    # --------------------------------------------------------

    formatted_registration_no = format_registration_no(
        student[0]
    )

    return render_template(
        "receipt.html",
        student=student,
        registration_no=formatted_registration_no
    )


# ============================================================
# STUDENT RECEIPT
# ============================================================

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
        <div style="font-family:Arial;text-align:center;padding:50px;">

            <h2>
                Payment Not Verified
            </h2>

            <p>
                Receipt केवल verified payment
                के बाद generate की जा सकती है।
            </p>

            <a href="/payment-status">
                Back to Payment Status
            </a>

        </div>
        """

    # --------------------------------------------------------
    # FORMATTED REGISTRATION NUMBER
    # --------------------------------------------------------

    formatted_registration_no = format_registration_no(
        student[0]
    )

    return render_template(
        "receipt.html",
        student=student,
        registration_no=formatted_registration_no
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
# START SERVER
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