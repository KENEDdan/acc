import secrets
import string

from django.contrib.auth import get_user_model


def generate_temp_password(length=10):
    """A random temporary password shown once to the admin who registers/resets a member."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_member_account(member):
    """
    Create a login account for a newly registered Member, using their member_id
    as the username (already unique) and a random temporary password.
    Returns the plaintext temporary password (only ever available this once)
    or None if the member already has an account.
    """
    if member.user_id:
        return None

    User = get_user_model()
    temp_password = generate_temp_password()
    first_name = (member.full_name or '').split(' ')[0][:150]

    user = User.objects.create_user(
        username=member.member_id,
        email=member.email or '',
        password=temp_password,
        first_name=first_name,
        role=User.Role.MEMBER,
        must_change_password=True,
    )
    member.user = user
    member.save(update_fields=['user'])
    return temp_password


def reset_member_password(member):
    """
    Admin-assisted password reset for a member who can't use the email-based
    self-service flow (no email on file, lost access, etc). Issues a fresh
    temporary password and forces a change on next login.
    """
    if not member.user_id:
        return create_member_account(member)

    User = get_user_model()
    temp_password = generate_temp_password()
    user = member.user
    user.set_password(temp_password)
    user.must_change_password = True
    user.is_active = True
    user.save(update_fields=['password', 'must_change_password', 'is_active'])
    return temp_password