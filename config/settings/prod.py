"""Production settings. Activate with DJANGO_SETTINGS_MODULE=config.settings.prod.

Everything here is hardening on top of base.py — no new features, just the
security posture Django's own `manage.py check --deploy` checklist expects
before a real deployment goes live.
"""
from decouple import config

from .base import *  # noqa: F401,F403
from .base import BASE_DIR

DEBUG = False

if not SECRET_KEY or SECRET_KEY.startswith('dev-secret') or len(SECRET_KEY) < 50:
    raise RuntimeError(
        "SECRET_KEY is missing or looks like a development placeholder. "
        "Generate a real one (e.g. `python -c \"from django.core.management.utils import "
        "get_random_secret_key; print(get_random_secret_key())\"`) and set it in the "
        "production .env before starting the app."
    )

if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['127.0.0.1', 'localhost']:
    raise RuntimeError(
        "ALLOWED_HOSTS is not set to a real domain. Set it in the production .env, "
        "e.g. ALLOWED_HOSTS=apostoliccampuschurch.org,www.apostoliccampuschurch.org"
    )

# Trust the reverse proxy's X-Forwarded-Proto header so Django knows a
# proxied request was actually HTTPS (needed behind nginx/a load balancer).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'

# Start conservative (1 day) rather than defaulting straight to a full year —
# HSTS is easy to lock yourself out of on a botched cert renewal. Ratchet
# SECURE_HSTS_SECONDS up (e.g. to 31536000) once HTTPS is confirmed solid.
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=86400, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)

# Static/media served by the app itself unless a CDN/object store is fronting
# them (see ADMIN readme for adding whitenoise or S3-backed storage later).
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
