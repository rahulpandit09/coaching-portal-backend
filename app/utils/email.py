import smtplib
from email.mime.text import MIMEText

from app.core.config import EMAIL_USER, EMAIL_PASS


def send_otp_email(receiver_email: str, otp: str):

    subject = "Reset Password OTP"

    body = f"""
Hello,

Your OTP for reset password is: {otp}

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
        server = smtplib.SMTP("smtp.gmail.com", 587)

        server.starttls()

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