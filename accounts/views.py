from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, login, get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from .two_factor import (
    generate_totp_secret, get_totp_uri, generate_qr_data_uri, verify_totp_code,
    generate_backup_codes, hash_backup_codes, verify_and_consume_backup_code,
)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            user.must_change_password = False
            user.save(update_fields=['must_change_password'])
            messages.success(request, "Your password has been updated.")
            return redirect('dashboard:redirect')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form, 'forced': request.user.must_change_password})


# ---------- Two-Factor Authentication ----------

@login_required
def two_factor_setup(request):
    user = request.user
    if user.two_factor_enabled:
        return redirect('accounts:two_factor_manage')

    if 'pending_totp_secret' not in request.session:
        request.session['pending_totp_secret'] = generate_totp_secret()
    secret = request.session['pending_totp_secret']
    uri = get_totp_uri(user, secret)
    qr_data_uri = generate_qr_data_uri(uri)

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        if verify_totp_code(secret, code):
            user.totp_secret = secret
            user.two_factor_enabled = True
            backup_codes = generate_backup_codes()
            user.two_factor_backup_codes = hash_backup_codes(backup_codes)
            user.save(update_fields=['totp_secret', 'two_factor_enabled', 'two_factor_backup_codes'])
            del request.session['pending_totp_secret']
            request.session['fresh_backup_codes'] = backup_codes
            messages.success(request, "Two-factor authentication is now enabled.")
            return redirect('accounts:two_factor_backup_codes')
        error = "That code didn't match. Please try again."

    return render(request, 'accounts/two_factor_setup.html', {
        'qr_data_uri': qr_data_uri, 'secret': secret, 'error': error,
    })


@login_required
def two_factor_backup_codes(request):
    """One-time display of freshly generated backup codes - only reachable right after generating them."""
    codes = request.session.pop('fresh_backup_codes', None)
    if not codes:
        return redirect('accounts:two_factor_manage')
    return render(request, 'accounts/two_factor_backup_codes.html', {'codes': codes})


@login_required
def two_factor_manage(request):
    return render(request, 'accounts/two_factor_manage.html')


@login_required
def two_factor_disable(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')
        if request.user.check_password(password):
            request.user.two_factor_enabled = False
            request.user.totp_secret = ''
            request.user.two_factor_backup_codes = ''
            request.user.save(update_fields=['two_factor_enabled', 'totp_secret', 'two_factor_backup_codes'])
            messages.success(request, "Two-factor authentication has been disabled.")
        else:
            messages.error(request, "Incorrect password - two-factor authentication was not disabled.")
    return redirect('accounts:two_factor_manage')


@login_required
def two_factor_regenerate_backup_codes(request):
    if request.method == 'POST' and request.user.two_factor_enabled:
        codes = generate_backup_codes()
        request.user.two_factor_backup_codes = hash_backup_codes(codes)
        request.user.save(update_fields=['two_factor_backup_codes'])
        request.session['fresh_backup_codes'] = codes
        return redirect('accounts:two_factor_backup_codes')
    return redirect('accounts:two_factor_manage')


def two_factor_verify(request):
    """The login-time verification step. Reached only after a correct username/password
    for an account that has 2FA enabled - see PortalLoginView.form_valid in core/views.py."""
    user_id = request.session.get('2fa_user_id')
    if not user_id:
        return redirect('core:portal')
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        return redirect('core:portal')

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        use_backup = request.POST.get('use_backup') == '1'
        valid = verify_and_consume_backup_code(user, code) if use_backup else verify_totp_code(user.totp_secret, code)
        if valid:
            del request.session['2fa_user_id']
            next_url = request.session.pop('2fa_next', None) or reverse('dashboard:redirect')
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect(next_url)
        error = "Invalid code. Please try again."
    return render(request, 'accounts/two_factor_verify.html', {'error': error})