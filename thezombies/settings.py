"""
Django settings for thezombies project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

TEMPLATE_DEBUG = True if os.getenv('TEMPLATE_DEBUG', 'True') == 'True' else DEBUG


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_hstore',
    'django_extensions',

    'django_atomic_signals',
    'django_atomic_celery',
    'thezombies',
)

if DEBUG:
    try:
        import debug_toolbar
        INSTALLED_APPS += ('debug_toolbar',)
    except ImportError:
        pass

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'thezombies.urls'

WSGI_APPLICATION = 'thezombies.wsgi.application'

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {'default': dj_database_url.config()}
DATABASES['default']['ENGINE'] = 'django_postgrespool'

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = os.getenv('USE_I18N', False) == 'True'

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
ALLOWED_HOSTS = ['*']

#  Media

MEDIA_ROOT = os.getenv('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))
MEDIA_URL = os.getenv('MEDIA_URL', '/media/')

# Celery
# See celeryconfig.py

# JSON Schema

DATA_CATALOG_SCHEMA_PATH = os.path.join(BASE_DIR, 'schema/1_0_final/catalog.json')

# Request timeout (seconds)

REQUEST_TIMEOUT = 60 * 3

# Redis (caching backend)

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
