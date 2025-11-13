import os
from sib_api_v3_sdk import ApiClient, TransactionalEmailsApi, SendSmtpEmail
from django.conf import settings

def send_brevo_email(to, subject, html_content, text_content=None):
    """Reusable Brevo API email sender"""
    
    client = ApiClient(settings.BREVO_CONFIGURATION)
    api = TransactionalEmailsApi(client)

    email = SendSmtpEmail(
        sender={"email": settings.BREVO_FROM, "name": "Sona Enterprises"},
        to=[{"email": to}],
        subject=subject,
        html_content=html_content,
        text_content=text_content or "",
    )

    try:
        api.send_transac_email(email)
        return True
    except Exception as e:
        print("Brevo API Email Error:", e)
        return False
