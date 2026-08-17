from django.shortcuts import redirect

EXEMPT_PATHS = ('/account/change-password/', '/logout/', '/static/', '/media/', '/admin/')
TWO_FA_EXEMPT_PATHS = ('/account/2fa/', '/account/change-password/', '/logout/', '/static/', '/media/', '/admin/')


class ForcePasswordChangeMiddleware:
    """
    If the logged-in user has must_change_password=True, every request except
    the exempt paths (the change-password page itself, logout, static/media,
    and the raw Django admin as a safety valve) gets redirected there first.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and getattr(user, 'must_change_password', False):
            if not any(request.path.startswith(p) for p in EXEMPT_PATHS):
                return redirect('accounts:change_password')
        return self.get_response(request)


class RequireTwoFactorMiddleware:
    """
    Accounts whose role handles money or full platform control (superadmin,
    and the finance admin roles) must have two-factor authentication set up.
    If they haven't enabled it yet, every request except the exempt paths
    gets redirected to the 2FA setup page first. This runs after the forced
    password-change check, so a brand-new account sets its own password
    before being asked to also set up 2FA.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and not getattr(user, 'must_change_password', False):
            from .two_factor import role_requires_2fa
            if role_requires_2fa(user) and not getattr(user, 'two_factor_enabled', False):
                if not any(request.path.startswith(p) for p in TWO_FA_EXEMPT_PATHS):
                    return redirect('accounts:two_factor_setup')
        return self.get_response(request)