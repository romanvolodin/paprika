from pathlib import Path

from environs import Env


env = Env()
env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = env.str("PAPRIKA_SECRET_KEY")
ALLOWED_HOSTS = env.list("PAPRIKA_ALLOWED_HOSTS", [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    #
    "corsheaders",
    "dmr",
    "dmr.security.jwt.blocklist",
    #
    "apps.core",
    "apps.access",
    "apps.chat",
    "apps.companies",
    "apps.feed",
    "apps.projects",
    "apps.shots",
    "apps.tasks",
    "apps.users",
    "apps.versions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
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
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Versions (see `apps.versions`). These are plain environment variables for
# now; the plan is to move them into per-project settings later.
#
# Max size of a single uploaded version file, in megabytes.
VERSION_MAX_FILE_SIZE_MB = env.int("PAPRIKA_VERSION_MAX_FILE_SIZE_MB", 2048)
# Which frame of a video becomes its thumbnail, as a fraction of the clip:
# 0.0 = first frame, 0.5 = middle, 1.0 = last frame.
VERSION_THUMB_FRAME_POSITION = env.float(
    "PAPRIKA_VERSION_THUMB_FRAME_POSITION",
    0.5,
    validate=lambda value: 0.0 <= value <= 1.0,
)
# Longest side of a generated thumbnail, in pixels.
VERSION_THUMB_MAX_SIZE = 320

# Chat (see `apps.chat`). Plain environment variables, like the versions
# ones above.
#
# Max length of a chat message's text, in characters.
CHAT_MESSAGE_MAX_LENGTH = env.int("PAPRIKA_CHAT_MESSAGE_MAX_LENGTH", 2000)
# Max size of a single chat attachment, in megabytes.
CHAT_ATTACHMENT_MAX_FILE_SIZE_MB = env.int(
    "PAPRIKA_CHAT_ATTACHMENT_MAX_FILE_SIZE_MB", 100
)
# Max number of attachments in a single message.
CHAT_MESSAGE_MAX_ATTACHMENTS = 10

# Importing shots from a spreadsheet (see `apps.shot_import`).
#
# Max number of shots in a single import request.
SHOT_IMPORT_MAX_ROWS = 2000

AUTH_USER_MODEL = "users.User"
