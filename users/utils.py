import requests
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


def enviar_email_resend(destinatario, asunto, cuerpo_texto, cuerpo_html=None):
    """
    Envía un mail vía la API HTTPS de Resend, evitando el bloqueo de SMTP en Railway.
    Devuelve (ok, detalle) — ok=False no rompe el flujo que lo llama.
    """
    payload = {
        'from': 'Brot Panes <no-reply@brotpanes.com.ar>',
        'to': [destinatario],
        'subject': asunto,
        'text': cuerpo_texto,
    }
    if cuerpo_html:
        payload['html'] = cuerpo_html

    try:
        response = requests.post(
            'https://api.resend.com/emails',
            json=payload,
            headers={
                'Authorization': f'Bearer {settings.RESEND_API_KEY}',
                'Content-Type': 'application/json',
            },
            timeout=10,
        )
        return response.status_code in (200, 201), response.text
    except Exception as e:
        return False, str(e)


def enviar_invitacion(user):
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"https://panel.brotpanes.com.ar/establecer-password/{uid}/{token}/"

    enviar_email_resend(
        user.email,
        'Bienvenido a Brot Panes',
        f'Hacé click en el siguiente link para crear tu contraseña: {link}',
    )