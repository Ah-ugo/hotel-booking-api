import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
from jinja2 import Environment, FileSystemLoader
from config.settings import settings
from models.newBooking import BookingWithDetails
from models.newPayment import PaymentResponse

# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader("templates"))


def send_email(to_email: str, subject: str, html_content: str, attachments=None):
    """
    Send an email using SMTP
    """
    # Create message
    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_FROM
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
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
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

