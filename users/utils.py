from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail

def enviar_invitacion(user):
    token_generator = PasswordResetTokenGenerator()
    token = token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"http://127.0.0.1:8000/panel/establecer-password/{uid}/{token}/"

    send_mail(
    'Bienvenido a Brot Panes',
    f'Hacé click en el siguiente link para crear tu contraseña: {link}',
    'no-reply@brotpanes.com',
    [user.email],
)