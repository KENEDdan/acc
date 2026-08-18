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

# Needed once you're behind an HTTPS reverse proxy — without it, Django rejects
# POST forms from the real domain because the Origin header is https:// but
# Django doesn't yet know to trust that scheme for CSRF purposes.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS', default='', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
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

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# --- Media storage ---
# Falls back to local disk (MEDIA_ROOT) unless a bucket is configured — but local
# disk isn't durable: a redeploy or lost server wipes every uploaded member photo,
# ID document, and giving proof-of-payment image with it. Set these before go-live.
# Works with AWS S3 directly, or any S3-compatible provider (DigitalOcean Spaces,
# Backblaze B2, etc.) via AWS_S3_ENDPOINT_URL.
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
if AWS_STORAGE_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='')
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='') or None
    AWS_DEFAULT_ACL = None  # bucket policy controls access; don't set per-object ACLs
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False

# --- Error monitoring ---
# No-ops until SENTRY_DSN is set — sign up at sentry.io (or self-host), create a
# Django project, and paste its DSN into the production .env.
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=config('SENTRY_TRACES_SAMPLE_RATE', default=0.0, cast=float),
        send_default_pii=False,
    )

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
