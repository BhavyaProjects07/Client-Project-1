import os
from pathlib import Path
from decouple import config
import dj_database_url

# -----------------------------
# BASE CONFIG
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = ['sona-enterprises.onrender.com', 'localhost', '127.0.0.1']

# -----------------------------
# INSTALLED APPS
# -----------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store',
    'storages',  # keep for future cloud/static storage support
]

# -----------------------------
# MIDDLEWARE
# -----------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Must stay above session middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]



# -----------------------------
# URL & TEMPLATE CONFIG
# -----------------------------
ROOT_URLCONF = 'Devki_Mart.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'Devki_Mart.wsgi.application'

# -----------------------------
# DATABASE CONFIG (Neon / SQLite)
# -----------------------------
DATABASE_URL = config("DATABASE_URL")

if DATABASE_URL.startswith("sqlite"):
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }

# -----------------------------
# PASSWORD VALIDATION
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------
# INTERNATIONALIZATION
# -----------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------------
# STATIC FILES
# -----------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ✅ Use WhiteNoise for static file handling
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -----------------------------
# MEDIA FILES (NO LOCAL STORAGE)
# -----------------------------
# ✅ Completely disable local media storage — handled by ImageKit SDK
MEDIA_URL = ''
MEDIA_ROOT = ''  # ensure no local media directory is created

# -----------------------------
# AUTH SYSTEM
# -----------------------------
AUTH_USER_MODEL = 'store.CustomUser'
LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/request-otp/'

# -----------------------------
# EMAIL CONFIG
# -----------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")  # app password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

ADMINS = [('DevkiMart Admin', 'laptopuse01824x@gmail.com')]

# -----------------------------
# IMAGEKIT CONFIGURATION
# -----------------------------
IMAGEKIT_PUBLIC_KEY = config('IMAGEKIT_PUBLIC_KEY')
IMAGEKIT_PRIVATE_KEY = config('IMAGEKIT_PRIVATE_KEY')
IMAGEKIT_URL_ENDPOINT = config('IMAGEKIT_URL_ENDPOINT')

if not all([IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT]):
    print("⚠️ WARNING: One or more ImageKit environment variables are missing!")

# -----------------------------
# DEBUG
# -----------------------------
DEBUG = True
