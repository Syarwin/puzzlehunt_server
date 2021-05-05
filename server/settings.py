
"""
Base Django settings for server project.
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import dj_database_url
from os.path import dirname, abspath
import codecs
codecs.register(lambda name: codecs.lookup('utf8') if name == 'utf8mb4' else None)

BASE_DIR = dirname(dirname(dirname(abspath(__file__))))

# Application definition
SITE_TITLE = "MindBreakers"

INSTALLED_APPS = (
    'bootstrap_admin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'base_site',
    'teams',
    'hunts',
    'crispy_forms',
    'huey.contrib.djhuey',
    "crispy_bootstrap5",
)

SITE_ID = 1  # For flatpages

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'hunts.middleware.HuntMiddleware',
    'teams.middleware.TeamMiddleware',
)

ROOT_URLCONF = 'server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [os.path.join(BASE_DIR, 'server/templates')],
        'OPTIONS': {
            'builtins': ['hunts.templatetags.hunt_tags',
                         'hunts.templatetags.prepuzzle_tags'],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "puzzlehunt"
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

HUEY = {
    'immediate': False,
    'connection': {
        'host': 'redis',
    },
    'consumer': {
        'workers': 2,
    },
}


WSGI_APPLICATION = 'server.wsgi.application'
ASGI_APPLICATION = 'server.routing.application'

CHANNEL_LAYERS = {
    'default': {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}

# URL settings
LOGIN_REDIRECT_URL = '/'
PROTECTED_URL = '/protected/'
LOGIN_URL = 'login'

# Random settings
SILENCED_SYSTEM_CHECKS = ["urls.W005"]  # silences admin url override warning
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
DEBUG_TOOLBAR_PATCH_SETTINGS = False
BOOTSTRAP_ADMIN_SIDEBAR_MENU = True
DEFAULT_HINT_LOCKOUT = 60  # 60 Minutes
HUNT_REGISTRATION_LOCKOUT = 2  # 2 Days

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static/Media files settings
STATIC_ROOT = "/static/"
STATIC_URL = '/static/'

MEDIA_ROOT = "/media/"
MEDIA_URL = '/media/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/external/django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'teams': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'hunts': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
    },
}

# Email settings
CONTACT_EMAIL = 'TODO@TODO.com'

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587

# Environment variable overrides
if os.environ.get("ENABLE_DEBUG_EMAIL"):
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = '/tmp/test_folder'

if os.environ.get("ENABLE_DEBUG_TOOLBAR"):
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
    MIDDLEWARE = ('debug_toolbar.middleware.DebugToolbarMiddleware',) + MIDDLEWARE

if os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[DjangoIntegration()],

        # Sends which user caused the error
        send_default_pii=True
    )



# ENV settings
DEBUG = os.getenv("DJANGO_ENABLE_DEBUG", default="False").lower() == "true"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DATABASES = {'default': dj_database_url.config(conn_max_age=600)}

if(DATABASES['default']['ENGINE'] == 'django.db.backends.mysql'):
    DATABASES['default']['OPTIONS'] = {'charset': 'utf8mb4'}

INTERNAL_IPS = ['127.0.0.1', 'localhost']
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_USER")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_PASSWORD")
DOMAIN = os.getenv("DOMAIN", default="default.com")

ALLOWED_HOSTS = ['*']