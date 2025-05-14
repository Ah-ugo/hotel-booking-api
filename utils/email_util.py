import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from models.newBooking import BookingWithDetails
from models.newPayment import PaymentResponse
from dotenv import load_dotenv
import aiosmtplib
import ssl

load_dotenv()

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))

# Email configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
# SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = "ahuekweprinceugo@gmail.com"
SMTP_PASSWORD = os.getenv("GMAIL_PASS")
FROM_EMAIL = "ahuekweprinceugo@gmail.com"



def send_email(to_email: str, subject: str, html_content: str, attachments=None):
    """
    Send an email using SMTP
    """
    # Create message
    msg = MIMEMultipart()
    msg["From"] = "ahuekweprinceugo@gmail.com"
    msg["To"] = to_email
    msg["Subject"] = subject

    # Attach HTML content
    msg.attach(MIMEText(html_content, "html"))

    # Attach files if any
    if attachments:
        for attachment in attachments:
            with open(attachment, "rb") as file:
                part = MIMEApplication(file.read(), Name=os.path.basename(attachment))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment)}"'
            msg.attach(part)

    # Send email
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.ehlo()
        # server.starttls()
        server.login("ahuekweprinceugo@gmail.com", os.getenv("GMAIL_PASS"))
        server.sendmail(msg["From"], [msg["To"]], msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False



# Gmail SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 465
EMAIL_ADDRESS = "ahuekweprinceugo@gmail.com"
PASSWORD = os.getenv("GMAIL_PASS")


async def send_reset_email(email_to: str, token: str):
    reset_link = f"https://hotel-booking-api-r5dd.onrender.com/api/auth/reset-password?token={token}"

    # Create message container
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Password Reset Request"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = email_to

    # Create the body of the message (plain and HTML versions)
    text = f"Please reset your password using this link: {reset_link}"
    html = f"""\
    <html>
      <body>
        <p>Please click the link below to reset your password:<br>
        <a href="{reset_link}">Reset Password</a></p>
        <p>This link will expire in 30 minutes.</p>
      </body>
    </html>
    """

    # Record the MIME types of both parts
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')

    # Attach parts to message
    msg.attach(part1)
    msg.attach(part2)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
            server.ehlo()
            server.login(EMAIL_ADDRESS, PASSWORD)
            server.sendmail(EMAIL_ADDRESS, [email_to], msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_booking_confirmation(booking: BookingWithDetails):
    """
    Send booking confirmation email
    """
    template = env.get_template("booking_confirmation.html")
    html_content = template.render(
        booking=booking,
        accommodation=booking.accommodation_details,
        user=booking.user_details
    )

    subject = f"Booking Confirmation - {booking.accommodation_details['name']}"

    return send_email(
        to_email=booking.user_details["email"],
        subject=subject,
        html_content=html_content
    )


def send_payment_receipt(payment: PaymentResponse, booking: BookingWithDetails):
    """
    Send payment receipt email
    """
    template = env.get_template("payment_receipt.html")
    html_content = template.render(
        payment=payment,
        booking=booking,
        accommodation=booking.accommodation_details,
        user=booking.user_details
    )

    subject = f"Payment Receipt - {booking.accommodation_details['name']}"

    return send_email(
        to_email=booking.user_details["email"],
        subject=subject,
        html_content=html_content
    )


def send_booking_reminder(booking: BookingWithDetails):
    """
    Send booking reminder email
    """
    template = env.get_template("booking_reminder.html")
    html_content = template.render(
        booking=booking,
        accommodation=booking.accommodation_details,
        user=booking.user_details
    )

    subject = f"Reminder: Your Stay at {booking.accommodation_details['name']}"

    return send_email(
        to_email=booking.user_details["email"],
        subject=subject,
        html_content=html_content
    )

