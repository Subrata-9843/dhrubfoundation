# Email template functions
from flask import render_template
from app import mail
from flask_mail import Message

def send_password_reset_email(admin, token):
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