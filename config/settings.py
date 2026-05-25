"""Settings for the healthcare prompt management project."""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        if '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


_load_dotenv_file(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-j)2!_q*a&+*g&0ho0nb#-uki4mt=)3i+z&_4e=xc+29+5nj0uq',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
    if host.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'prompts.apps.PromptsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MONGODB_URI = os.environ.get('PROMPT_MANAGER_MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB_NAME = os.environ.get('PROMPT_MANAGER_MONGODB_DB', 'prompt_manager')
MONGODB_DEPARTMENTS_COLLECTION = os.environ.get('PROMPT_MANAGER_MONGODB_DEPARTMENTS_COLLECTION', 'departments')
MONGODB_PROMPTS_COLLECTION = os.environ.get('PROMPT_MANAGER_MONGODB_PROMPTS_COLLECTION', 'prompts')

PROMPT_MANAGER_LLM_PROVIDER = os.environ.get('PROMPT_MANAGER_LLM_PROVIDER', 'azure_openai')
PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT = os.environ.get(
    'PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT',
    os.environ.get('PROMPT_MANAGER_TEST_API_URL', ''),
)
PROMPT_MANAGER_AZURE_OPENAI_API_KEY = os.environ.get(
    'PROMPT_MANAGER_AZURE_OPENAI_API_KEY',
    os.environ.get('PROMPT_MANAGER_TEST_API_KEY', ''),
)
PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT = os.environ.get(
    'PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT',
    os.environ.get('PROMPT_MANAGER_TEST_MODEL', ''),
)
PROMPT_MANAGER_AZURE_OPENAI_API_VERSION = os.environ.get(
    'PROMPT_MANAGER_AZURE_OPENAI_API_VERSION',
    '2024-10-21',
)
PROMPT_MANAGER_TEST_TIMEOUT_SECONDS = int(
    os.environ.get('PROMPT_MANAGER_TEST_TIMEOUT_SECONDS', '30')
)
