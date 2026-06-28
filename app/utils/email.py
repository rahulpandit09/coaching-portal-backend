import smtplib
from email.mime.text import MIMEText

from app.core.config import EMAIL_USER, EMAIL_PASS


def send_otp_email(receiver_email: str, otp: str):

    subject = "Password Reset OTP"

    body = f"""
Hello,

Your OTP for password reset is: {otp}

This OTP will expire in 60 seconds.

Do not share this OTP with anyone.

Regards,
Coaching Portal Team
"""

    msg = MIMEText(body)

    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = receiver_email

    try:
        # Force IPv4 by binding the source address to 0.0.0.0
        # This fixes the 'Network is unreachable' Errno 101 on Render which lacks IPv6 routing
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10, source_address=('0.0.0.0', 0))

        server.login(
            EMAIL_USER,
            EMAIL_PASS
        )

        server.sendmail(
            EMAIL_USER,
            receiver_email,
            msg.as_string()
        )

        server.quit()

        print("Email sent successfully")

    except Exception as e:
        print("Email sending failed:", e)