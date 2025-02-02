from pathlib import Path

from environs import Env


env = Env()
env.read_env(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = env.str("PAPRIKA_SECRET_KEY")
DEBUG = env.bool("PAPRIKA_DEBUG", False)
ALLOWED_HOSTS = env.list("PAPRIKA_ALLOWED_HOSTS", [])

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    #
    "colorfield",
    "corsheaders",
    #
    "core",
    "users",
    "chat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "paprika.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "paprika.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env.str("POSTGRES_HOST", "localhost"),
        "PORT": env.int("POSTGRES_PORT", 5432),
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "/users/login/"

ASGI_APPLICATION = "paprika.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("paprika-redis", 6379)],
        },
    },
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 1_048_576  # 100MB

CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
