import io
import base64
import json
import secrets
from datetime import datetime, timedelta
import hmac

import pyotp
import qrcode
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

ROLES_REQUIRING_2FA = ('superadmin', 'church_finance', 'gym_finance', 'aff_finance')
EMAIL_OTP_VALIDITY_MINUTES = 10


def role_requires_2fa(user):
    return user.role in ROLES_REQUIRING_2FA


def generate_totp_secret():
    return pyotp.random_base32()


def get_totp_uri(user, secret):
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.username, issuer_name="Apostolic Campus Church"
    )


def generate_qr_data_uri(data):
    """Render a QR code in memory and return it as a base64 data URI, ready for an <img src=...>."""
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    encoded = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:image/png;base64,{encoded}"


def verify_totp_code(secret, code):
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count=8):
    return [secrets.token_hex(4) for _ in range(count)]


def hash_backup_codes(codes):
    return json.dumps([make_password(c) for c in codes])


def verify_and_consume_backup_code(user, submitted_code):
    """Checks a backup code and, if valid, removes it so it can't be reused. Saves the user."""
    if not user.two_factor_backup_codes or not submitted_code:
        return False
    hashed_list = json.loads(user.two_factor_backup_codes)
    for hashed in hashed_list:
        if check_password(submitted_code, hashed):
            hashed_list.remove(hashed)
            user.two_factor_backup_codes = json.dumps(hashed_list)
            user.save(update_fields=['two_factor_backup_codes'])
            return True
    return False


def send_email_otp(user, request):
    """Emails a one-time verification code as an alternative to the authenticator app,
    for a user who has an email address on file. The code is stashed in the (pre-auth)
    session tied to this login attempt, not the database — it's short-lived and only
    ever relevant to the one login flow that requested it. Returns False without
    sending anything if the account has no email on file."""
    if not user.email:
        return False
    from django.conf import settings
    from django.core.mail import send_mail

    code = f"{secrets.randbelow(1000000):06d}"
    request.session['2fa_email_code'] = code
    request.session['2fa_email_code_sent_at'] = timezone.now().isoformat()
    send_mail(
        subject="Your Apostolic Campus Church verification code",
        message=(
            f"Your verification code is: {code}\n\n"
            f"This code expires in {EMAIL_OTP_VALIDITY_MINUTES} minutes. "
            "If you didn't try to log in, you can safely ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return True


def verify_email_otp(request, submitted_code):
    """Checks a code sent by send_email_otp against the pending login's session,
    enforcing expiry and single use."""
    stored_code = request.session.get('2fa_email_code')
    sent_at_str = request.session.get('2fa_email_code_sent_at')
    if not stored_code or not sent_at_str or not submitted_code:
        return False
    if timezone.now() - datetime.fromisoformat(sent_at_str) > timedelta(minutes=EMAIL_OTP_VALIDITY_MINUTES):
        return False
    if not hmac.compare_digest(submitted_code, stored_code):
        return False
    del request.session['2fa_email_code']
    del request.session['2fa_email_code_sent_at']
    return True