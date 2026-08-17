import io
import base64
import json
import secrets

import pyotp
import qrcode
from django.contrib.auth.hashers import make_password, check_password

ROLES_REQUIRING_2FA = ('superadmin', 'church_finance', 'gym_finance', 'aff_finance')


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