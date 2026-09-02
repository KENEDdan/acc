from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
# Separate from SECRET_KEY on purpose — used for application-level field
# encryption (accounts.fields.EncryptedCharField), so rotating one doesn't
# force rotating the other. Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Used to build absolute links in emails (notifications, etc.) sent from code
# paths that don't have a `request` to call build_absolute_uri() on. Set this
# to the real https:// domain in production.
SITE_BASE_URL = config('SITE_BASE_URL', default='http://127.0.0.1:8000')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=lambda v: [s.strip() for s in v.split(',')])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',

    'django_celery_beat',

    'accounts',
    'core',
    'newsfeed',
    'church',
    'gym',
    'aff',
    'finance',
    'notifications',
    'dashboard',
    'audit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.ForcePasswordChangeMiddleware',
    'accounts.middleware.RequireTwoFactorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notifications_context',
                'core.context_processors.site_contact_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Most managed Postgres providers (DigitalOcean, RDS, Render, Supabase, etc.) require
# SSL and will refuse plain connections. 'prefer' (the default) uses SSL when
# available without breaking local dev, which has none — set DB_SSLMODE=require (or
# verify-full, with DB_SSLROOTCERT pointing at the provider's CA bundle) once you're
# pointed at the managed instance.
_db_options = {'sslmode': config('DB_SSLMODE', default='prefer')}
_db_sslrootcert = config('DB_SSLROOTCERT', default='')
if _db_sslrootcert:
    _db_options['sslrootcert'] = _db_sslrootcert

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'OPTIONS': _db_options,
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'Arabic'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Africa/Juba'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CELERY_BROKER_URL = config('REDIS_URL')
CELERY_RESULT_BACKEND = config('REDIS_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Shared across processes (unlike the default in-memory cache), which the rate
# limiting on the public forms/AI assistant needs to actually be enforced
# correctly once there's more than one gunicorn worker.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL'),
    }
}

LOGIN_URL = '/portal/'
LOGIN_REDIRECT_URL = '/dashboard/redirect/'

# Email — used for password reset. Defaults to printing emails to the console
# (visible in your `runserver` terminal) so password reset works in dev without
# needing real SMTP credentials. For production, set these in .env:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST=smtp.yourprovider.com
#   EMAIL_PORT=587
#   EMAIL_USE_TLS=True
#   EMAIL_HOST_USER=you@yourdomain.com
#   EMAIL_HOST_PASSWORD=your-smtp-password
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='no-reply@apostoliccampuschurch.org')
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour, in seconds, for a reset link to stay valid
LOGOUT_REDIRECT_URL = '/'