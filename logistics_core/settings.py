"""
Django settings for logistics_core project.

Generated by 'django-admin startproject' using Django 5.2.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""
import os
import sys
import logging
from pathlib import Path

# --- Environment Variable Loading (Should be at the top) ---
# Attempt to load environment variables from a .env file (commonly used pattern)
# You might need to install python-dotenv: pip install python-dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    
    # Correct path assuming env_var.env is in the project root directory (M:\Documents\Logistics)
    # BASE_DIR is M:\Documents\Logistics
    env_path = BASE_DIR / 'env_var.env' 
    # Alternatively:
    # env_path = Path(__file__).resolve().parent.parent / 'env_var.env'

    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logging.info(f"Loaded environment variables from {env_path}")
    else:
        logging.warning(f"Environment file not found at {env_path}. Relying on system environment variables.")

except ImportError:
    logging.warning("python-dotenv is not installed. Relying on system environment variables.")
    pass

# --- End Environment Variable Loading ---

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-dev-only') # Provide a default for local dev if not set

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS_STRING = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STRING.split(',') if host.strip()]
if DEBUG and not ALLOWED_HOSTS: # Default for DEBUG mode if not specified
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
# Main: ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',
    # Your applications
    'fleet',
    'assignment',
    'monitoring',
    'shipments',
    'route_optimizer', # Ensure route_optimizer is here
    'corsheaders',
    'django_filters'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware'
]

ROOT_URLCONF = 'logistics_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [], # Add project-level template dirs if any: [BASE_DIR / 'templates']
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

WSGI_APPLICATION = 'logistics_core.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Colombo'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # For collectstatic in production
# STATICFILES_DIRS = [BASE_DIR / 'static'] # For project-level static files during development

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Project Specific Settings ---

# TODO: move this to environment
ENABLE_FLEET_EXTENDED_MODELS = os.getenv('ENABLE_FLEET_EXTENDED_MODELS', 'False').lower() == 'true'

# Kafka settings
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', "localhost:9092")

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
]

# --- Route Optimizer App Specific Settings (and other shared settings) ---

# Determine if we're in test mode (important for logic below)
# This is a common way to detect if `manage.py test` or `pytest` is running.
TESTING = 'test' in sys.argv or 'pytest' in sys.modules # Pytest check might need adjustment based on how it's run.

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# For production, use environment variables for database credentials.
# Example for PostgreSQL:
# DB_ENGINE = os.getenv('DB_ENGINE', 'django.db.backends.sqlite3')
# DB_NAME = os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3')
# DB_USER = os.getenv('DB_USER')
# DB_PASSWORD = os.getenv('DB_PASSWORD')
# DB_HOST = os.getenv('DB_HOST')
# DB_PORT = os.getenv('DB_PORT')

# DATABASES = {
#     'default': {
#         'ENGINE': DB_ENGINE,
#         'NAME': DB_NAME,
#         'USER': DB_USER,
#         'PASSWORD': DB_PASSWORD,
#         'HOST': DB_HOST,
#         'PORT': DB_PORT,
#     }
# }
# If DB_ENGINE is sqlite3, some fields like USER, PASSWORD, HOST, PORT might not be needed or empty.

if TESTING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',  # Use in-memory SQLite for tests
        }
    }
    # You might want to set other test-specific settings here,
    # e.g., disable DEBUG, use dummy cache, etc.
    # DEBUG = False # Usually good for tests
    # CACHES = {
    #     'default': {
    #         'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    #     }
    # }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3', # Your regular development database
        }
    }

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
if not GOOGLE_MAPS_API_KEY:
    if not TESTING and DEBUG: # Only raise error if not testing and not in debug mode for flexibility
        logging.warning("Google Maps API key is not set. Set the GOOGLE_MAPS_API_KEY environment variable.")
        GOOGLE_MAPS_API_KEY = "YOUR_API_KEY_IS_MISSING_IN_ENV" # Placeholder to avoid crashing non-test, debug env
    elif not TESTING and not DEBUG:
         raise ValueError("Google Maps API key is required for production. Set the GOOGLE_MAPS_API_KEY environment variable.")
    # For testing, this will be overridden in test_settings.py
    # If it reaches here during tests and is not set, it means test_settings didn't override.

GOOGLE_MAPS_API_URL = os.getenv('GOOGLE_MAPS_API_URL', 'https://maps.googleapis.com/maps/api/distancematrix/json')
USE_API_BY_DEFAULT = os.getenv('USE_API_BY_DEFAULT', 'False').lower() == 'true'

# API request settings (can be prefixed like ROUTE_OPTIMIZER_MAX_RETRIES if desired for clarity)
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
BACKOFF_FACTOR = float(os.getenv('BACKOFF_FACTOR', '2.0'))
RETRY_DELAY_SECONDS = float(os.getenv('RETRY_DELAY_SECONDS', '1.0'))
CACHE_EXPIRY_DAYS = int(os.getenv('CACHE_EXPIRY_DAYS', '30'))

# Cache settings (Define ONCE)
CACHES = {
    'default': {
        'BACKEND': os.getenv('DJANGO_CACHE_BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': os.getenv('DJANGO_CACHE_LOCATION', 'unique-snowflake'), # For locmem, this is just an identifier
        # For Redis/Memcached, LOCATION would be 'redis://127.0.0.1:6379/1' or '127.0.0.1:11211'
    }
}
OPTIMIZATION_RESULT_CACHE_TIMEOUT = int(os.getenv('OPTIMIZATION_RESULT_CACHE_TIMEOUT', '3600')) # 1 hour


# Logging Configuration (Example - Customize as needed)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        # Example: File handler
        # 'file': {
        #     'level': 'DEBUG',
        #     'class': 'logging.FileHandler',
        #     'filename': BASE_DIR / 'debug.log',
        #     'formatter': 'verbose',
        # },
    },
    'root': {
        'handlers': ['console'], # Add 'file' here if using file logging
        'level': 'INFO', # Default logging level for the project
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'route_optimizer': { # Specific logger for your app
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO', # More verbose for your app during debug
            'propagate': False,
        },
    }
}

