import requests
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


def enviar_email_resend(destinatario, asunto, cuerpo_texto, cuerpo_html=None):
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

    cuerpo_texto = f'Hacé click en el siguiente link para crear tu contraseña: {link}'

    cuerpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; background: #ffffff;">
        <div style="text-align: center; margin-bottom: 32px;">
            <h1 style="color: #1a1a1a; font-size: 24px; margin: 0;">Brot Panes</h1>
        </div>
        <div style="background: #f9f9f9; border-radius: 8px; padding: 32px;">
            <h2 style="color: #1a1a1a; font-size: 20px; margin: 0 0 16px 0;">Bienvenido al panel</h2>
            <p style="color: #444; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
                Tu usuario fue creado. Hacé click en el botón para establecer tu contraseña y acceder al panel.
            </p>
            <div style="text-align: center; margin: 0 0 24px 0;">
                <a href="{link}"
                   style="background: #e8521a; color: #ffffff; text-decoration: none;
                          padding: 14px 32px; border-radius: 6px; font-size: 15px;
                          font-weight: 600; display: inline-block;">
                    Crear contraseña
                </a>
            </div>
            <p style="color: #888; font-size: 13px; margin: 0;">
                Si el botón no funciona, copiá este link en tu navegador:<br>
                <a href="{link}" style="color: #e8521a; word-break: break-all;">{link}</a>
            </p>
        </div>
        <p style="color: #aaa; font-size: 12px; text-align: center; margin-top: 24px;">
            Brot Panes · Córdoba, Argentina
        </p>
    </div>
    """

    enviar_email_resend(user.email, 'Bienvenido a Brot Panes', cuerpo_texto, cuerpo_html)