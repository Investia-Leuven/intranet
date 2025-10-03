import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def _log(level: str, msg: str, **kwargs):
    meta = " ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
    print(f"[{level}] {msg} {meta}".strip())

def send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not (SMTP_HOST and EMAIL_USER and EMAIL_PASS):
        _log("ERROR", "Email env vars missing", host=SMTP_HOST, user=EMAIL_USER)
        return False
    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [to_email], msg.as_string())
        _log("INFO", "Email sent", to=to_email, subject=subject)
        return True
    except Exception as e:
        _log("ERROR", "Failed to send email", to=to_email, subject=subject, error=str(e))
        return False

def build_reset_email_body(username: str, reset_code: str) -> str:
    return f"""
    <html>
      <body>
        <p>Hi {username},</p>
        <p>You requested to reset your password for the Investia intranet.</p>
        <p>Your reset code is:</p>
        <p style='font-size: 18px; font-weight: bold; letter-spacing: 1px;'>{reset_code}</p>
        <p>Enter this code in the app to proceed. If you did not request this, you can ignore this email.</p>
        <p>Kind regards,<br/>Investia</p>
      </body>
    </html>
    """

def send_reset_email(username: str, to_email: str, reset_code: str) -> bool:
    subject = "Reset your Investia intranet password"
    body = build_reset_email_body(username, reset_code)
    return send_email(to_email, subject, body)