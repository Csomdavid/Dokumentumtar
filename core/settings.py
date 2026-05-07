from pathlib import Path
import os
from dotenv import load_dotenv

# Főkönyvtár definiálása (BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent

# .env fájl helye a betöltéshez
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY')
APP_ENV = os.getenv('APP_ENV', 'prod').lower().strip()

# Fejlesztői mód beállítása az APP_ENV alapján
DEBUG = (APP_ENV == 'dev')

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dokumentumtar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation

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

LANGUAGE_CODE = 'hu'

TIME_ZONE = 'Europe/Budapest'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = 'static/'

# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'dokumentumtar.Employee'

# ADATTÁROLÁSI ÚTVONALAK (Relatív a projekthez)
STORAGE_DIR = BASE_DIR / 'storage'
UPLOADS_DIR = STORAGE_DIR / 'uploads'
TEMP_DIR = STORAGE_DIR / 'temp'

# Automatikus mappalétrehozás
for folder in [UPLOADS_DIR, TEMP_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# A főoldalra ugorjon a rendszer sikeres bejelentkezés után 
LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/accounts/login/'

# BIZTONSÁGI MUNKAMENET-KEZELÉS (Session Security)

# A munkamenet hossza másodpercben (15 perc = 15 * 60 = 900 másodperc)
SESSION_COOKIE_AGE = 900

# A böngésző bezárásakor automatikusan léptesse ki a felhasználót
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Minden egyes kattintásnál/kérésnél frissítse a lejárati időt (Rolling Session)
# Így csak akkor lép ki 15 perc után, ha tényleg nem csinált semmit.
SESSION_SAVE_EVERY_REQUEST = True

# Megakadályozza, hogy JavaScriptből hozzáférjenek a munkamenet-sütihez (XSS védelem)
SESSION_COOKIE_HTTPONLY = True

# Csak HTTPS kapcsolaton keresztül küldje el a sütit
SESSION_COOKIE_SECURE = (APP_ENV == 'prod')
