# emails.py
import io
from flask import render_template
from app import mail
from flask_mail import Message
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_pdf_receipt(donation):
    """
    Generate a PDF receipt for a donation.
    Returns the PDF as bytes for attaching to emails.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, 770, "Donation Receipt")

    # Logo or NGO Name
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 740, "Dhrub Foundation")
    p.setFont("Helvetica", 10)
    p.drawString(100, 725, "Helping poor children live with dignity")
    p.drawString(100, 710, "Website: https://your-ngo-website.com")
    p.drawString(100, 695, "Email: contact@your-ngo-website.com")

    # Donation details
    p.setFont("Helvetica", 12)
    y = 660
    p.drawString(100, y, f"Receipt ID: {donation.id}")
    p.drawString(100, y - 20, f"Donor Name: {donation.donor_name or 'Anonymous'}")
    p.drawString(100, y - 40, f"Email: {donation.email}")
    p.drawString(100, y - 60, f"Amount: ₹{donation.amount:,.2f}")
    p.drawString(100, y - 80, f"Payment Method: {donation.payment_method}")
    p.drawString(100, y - 100, f"Date: {donation.date.strftime('%Y-%m-%d %H:%M:%S')}")

    # Footer
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, 60, "Thank you for your generous support!")
    p.drawString(100, 45, "This is an auto-generated receipt and does not require a signature.")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.read()


def send_password_reset_email(admin, token):
    """
    Send an email to the admin with a password reset link.
    """
    msg = Message(
        "Password Reset Request",
        recipients=[admin.email],
        html=render_template(
            'admin/email/reset_password.html',
            admin=admin,
            token=token
        )
    )
    mail.send(msg)


def send_donation_receipt(donation):
    """
    Send an email with a donation receipt PDF attached.
    """
    msg = Message(
        "Donation Receipt",
        recipients=[donation.email],
        html=render_template(
            'email/donation_receipt.html',
            donation=donation
        ),
        attachments=[(
            f"receipt_{donation.id}.pdf",
            "application/pdf",
            generate_pdf_receipt(donation)
        )]
    )
    mail.send(msg)
