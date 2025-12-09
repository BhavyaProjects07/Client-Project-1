import os
from pathlib import Path
from decouple import config
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api

# -----------------------------
# BASE CONFIG
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = ['newway-online.onrender.com', 'localhost', '127.0.0.1']

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
    'cloudinary',
    'cloudinary_storage',
    'ckeditor',
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
                'store.context_processors.business_details',  # Custom context processor
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
# MEDIA FILES (CLOUDINARY)
# -----------------------------
MEDIA_URL = '/media/'

# ✅ Cloudinary Configuration
cloudinary.config(
    cloud_name=config("CLOUDINARY_CLOUD_NAME"),
    api_key=config("CLOUDINARY_API_KEY"),
    api_secret=config("CLOUDINARY_API_SECRET"),
    secure=True
)

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# -----------------------------
# AUTH SYSTEM
# -----------------------------
AUTH_USER_MODEL = 'store.CustomUser'
LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/request-otp/'

ADMIN_VERIFY_CODE = config("ADMIN_VERIFY_CODE")


from sib_api_v3_sdk import Configuration

BREVO_API_KEY = config("BREVO_API_KEY")
BREVO_FROM = config("BREVO_FROM")

# Brevo API CONFIG
BREVO_CONFIGURATION = Configuration()
BREVO_CONFIGURATION.api_key["api-key"] = BREVO_API_KEY


ADMIN_EMAIL = config("ADMIN_EMAIL")
DELIVERY_VERIFY_CODE = config("DELIVERY_VERIFY_CODE")



# razorpay config
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID_TEST")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET_TEST")


# -----------------------------
# DEBUG
# -----------------------------
DEBUG = True


# Keep users logged in for 15 days
SESSION_COOKIE_AGE = 15 * 24 * 60 * 60     # 15 days in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False    # Do NOT expire when the browser closes
SESSION_COOKIE_SECURE = False              # True if using HTTPS
SESSION_SAVE_EVERY_REQUEST = True          # Refresh expiry every new request
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
