"""Django settings. Everything secret or environment-specific comes from environment variables / .env."""
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if SECRET_KEY == "change-me":          # the placeholder from .env.example
    SECRET_KEY = None
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set to a long random value when DJANGO_DEBUG=false")
    SECRET_KEY = "dev-only-insecure-key"
    warnings.warn("Using an insecure development SECRET_KEY; set DJANGO_SECRET_KEY in .env")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "apps.accounts",
    "apps.documents",
    "apps.chat",
    "apps.analytics",
    "apps.web",
]

# Product name shown in the UI (one place to change it; can also be set in .env)
PRODUCT_NAME = os.getenv("PRODUCT_NAME", "المرشد الأكاديمي الذكي")
PRODUCT_NAME_EN = os.getenv("PRODUCT_NAME_EN", "Smart Academic Advisor")
# Show the demo account credentials on the login page (for judges). Turn off for real users.
SHOW_DEMO_ACCOUNTS = os.getenv("SHOW_DEMO_ACCOUNTS", "true").lower() == "true"
# Used by `manage.py create_demo_accounts` and shown on the login page when SHOW_DEMO_ACCOUNTS is on.
DEMO_STUDENT_PASSWORD = os.getenv("DEMO_STUDENT_PASSWORD") or "student-demo-2026"
DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD") or "admin-demo-2026"

LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:chat"
LOGOUT_REDIRECT_URL = "web:login"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "apps.web.context_processors.product",
    ]},
}]

if os.getenv("DATABASE_URL"):
    # Hosted database (e.g. Render PostgreSQL): survives restarts and redeploys.
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600,
                                                  conn_health_checks=True)}
else:
    # Local development: a SQLite file next to manage.py.
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.getenv("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3")),
    }}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ar"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Production: hashed + compressed files (needs `collectstatic`). Development/tests: plain files.
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
                    else "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploads
MAX_UPLOAD_MB = 20
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_MB * 1024 * 1024 + 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# CORS (separate frontend during development)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")

REST_FRAMEWORK = {
    # Token: external clients (mobile app, API tools). Session: the Django web UI in apps/web,
    # which also enforces CSRF on every POST/PATCH/DELETE. Token is first so unauthenticated
    # requests still get 401 (not 403).
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication",
                                       "rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.errors.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"ask": os.getenv("ASK_RATE_LIMIT", "20/min"),
                               "auth": os.getenv("AUTH_RATE_LIMIT", "10/min")},   # login/register per IP
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"apps": {"handlers": ["console"], "level": "INFO"}},
}
